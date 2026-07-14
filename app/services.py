import requests
import os
import json
import time
from dotenv import load_dotenv, find_dotenv
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Load .env from project tree or fallback locations
def _load_project_env():
    found = find_dotenv()
    if found:
        load_dotenv(found)
        return

    alt_path = os.path.join(os.getcwd(), "requirements.txt", ".env")
    if os.path.exists(alt_path):
        load_dotenv(alt_path)
        return

    load_dotenv()


_load_project_env()

# Manual fallback parse for stubborn .env files
if not os.getenv("OPENROUTER_API_KEY"):
    alt_path = os.path.join(os.getcwd(), "requirements.txt", ".env")
    if os.path.exists(alt_path):
        try:
            with open(alt_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("OPENROUTER_API_KEY"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            os.environ["OPENROUTER_API_KEY"] = parts[1].strip()
                            break
        except Exception:
            pass


def call_ai(prompt: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Add it to your environment or .env file."
        )

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    model = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}

    max_retries = 5
    backoff = 1.0
    timeout = 30

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as e:
            if attempt == max_retries:
                raise RuntimeError(f"Network error calling API: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        try:
            data = response.json()
        except ValueError:
            if 500 <= response.status_code < 600 and attempt < max_retries:
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            raise RuntimeError(f"Non-JSON response from API (status {response.status_code}): {response.text}")

        if response.status_code == 429:
            retry_after = None
            try:
                retry_after = data.get("error", {}).get("metadata", {}).get("retry_after_seconds")
            except Exception:
                retry_after = None

            if not retry_after:
                retry_after = response.headers.get("Retry-After")
                try:
                    retry_after = float(retry_after) if retry_after is not None else None
                except Exception:
                    retry_after = None

            if retry_after:
                time.sleep(float(retry_after))
            else:
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)

            if attempt == max_retries:
                raise RuntimeError(f"API rate-limited after {max_retries} attempts: {data}")
            continue

        if 500 <= response.status_code < 600 and attempt < max_retries:
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if response.status_code != 200:
            raise RuntimeError(f"API error {response.status_code}: {data}")

        if "choices" not in data:
            raise RuntimeError(f"API response missing 'choices': {data}")

        return data["choices"][0]["message"]["content"]


def extract_cv_data(cv_text: str) -> dict:
    prompt = f"""
    Extract structured information from this CV.
    Return ONLY a valid JSON object, no markdown, nothing else:
    {{
        "name": "candidate name",
        "skills": ["skill1", "skill2"],
        "experience_years": 3,
        "summary": "brief professional summary"
    }}

    CV Text:
    {cv_text}
    """

    result = call_ai(prompt)
    result = result.replace("```json", "").replace("```", "").strip()
    return json.loads(result)


def save_candidates(candidate_data: dict) -> dict:
    """Insert or update a candidate record in `data/candidates.json`."""
    os.makedirs("data", exist_ok=True)
    candidates = []
    try:
        with open("data/candidates.json", "r", encoding="utf-8") as f:
            candidates = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        candidates = []

    candidate_name = candidate_data.get("name", "").strip().lower()
    existing_index = next(
        (
            index
            for index, candidate in enumerate(candidates)
            if candidate.get("name", "").strip().lower() == candidate_name
        ),
        None,
    )

    if existing_index is not None:
        candidate_data["id"] = candidates[existing_index].get("id", existing_index + 1)
        candidates[existing_index] = candidate_data
    else:
        candidate_data["id"] = len(candidates) + 1
        candidates.append(candidate_data)

    with open("data/candidates.json", "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)

    return candidate_data


def save_job(job_data: dict):
    try:
        with open(f"{BASE_DIR}/data/jobs.json", "r", encoding="utf-8") as f:
            jobs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        jobs = []
    
    job_data["id"] = len(jobs) + 1
    jobs.append(job_data)
    
    os.makedirs(f"{BASE_DIR}/data", exist_ok=True)
    with open(f"{BASE_DIR}/data/jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)
    
    return job_data

def match_candidates(job_id: int):
    jobs_path = os.path.join(BASE_DIR, "data", "jobs.json")
    candidates_path = os.path.join(BASE_DIR, "data", "candidates.json")

    try:
        with open(jobs_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    job = next((j for j in jobs if j.get("id") == job_id), None)
    if not job:
        return []

    try:
        with open(candidates_path, "r", encoding="utf-8") as f:
            candidates = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        candidates = []

    results = []
    required_skills = set(job.get("required_skills", []))
    best_by_name = {}

    for candidate in candidates:
        if not candidate.get("name") or not isinstance(candidate.get("skills"), list):
            continue

        score = 0
        cand_skills = set(candidate.get("skills", []))
        matching_skills = list(cand_skills & required_skills)
        score += candidate.get("experience_years", 0) * 5
        score += len(matching_skills) * 10

        result = {
            "candidate": candidate,
            "score": score,
            "matching_skills": matching_skills,
        }

        name_key = candidate.get("name", "").strip().lower()
        existing = best_by_name.get(name_key)
        if existing is None or result["score"] > existing["score"]:
            best_by_name[name_key] = result

    results = list(best_by_name.values())

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10]


def extract_job_data(job_text: str) -> dict:
    prompt = f"""
    Extract structured information from this job description.
    Return only a valid JSON object, no markdown, nothing else:
    {{
        "title": "job title",
        "required_skills": ["skill1", "skill2"],
        "min_experience_years": 2,
        "summary": "breif role summary"
    }}

    Job Description:
    {job_text}
    """
    result = call_ai(prompt)
    result = result.replace("```json", "").replace("```", "").strip()
    return json.loads(result)    