import requests
import os
import json
import time
from dotenv import load_dotenv, find_dotenv
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

chroma_client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_data"))

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


def get_candidates_collection():
    """Fetch the candidates collection fresh each time.

    If rebuild_chroma.py deletes & recreates collections while the server
    is running, stale module-level references would point to deleted
    collections. Fetching on every call avoids that.
    """
    return chroma_client.get_or_create_collection(
        name="candidates", embedding_function=embedding_fn
    )


def get_jobs_collection():
    """Fetch the jobs collection fresh each time (see above)."""
    return chroma_client.get_or_create_collection(
        name="jobs", embedding_function=embedding_fn
    )

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


def _call_model(model: str, prompt: str, api_key: str, timeout: int = 30) -> str:
    """Call a single OpenRouter model. Returns the text response or raises."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}

    max_retries = 3
    backoff = 1.0

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as e:
            if attempt == max_retries:
                raise RuntimeError(f"Network error calling {model}: {e}")
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
            raise RuntimeError(f"Non-JSON response from {model} (status {response.status_code}): {response.text}")

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
                raise RuntimeError(f"{model} rate-limited after {max_retries} attempts: {data}")
            continue

        if 500 <= response.status_code < 600 and attempt < max_retries:
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if response.status_code != 200:
            raise RuntimeError(f"{model} API error {response.status_code}: {data}")

        if "choices" not in data:
            raise RuntimeError(f"{model} response missing 'choices': {data}")

        return data["choices"][0]["message"]["content"]

    raise RuntimeError(f"{model} failed after {max_retries} retries")


def call_ai(prompt: str) -> str:
    """Call AI with fallback: primary model first, backup model if primary fails."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Add it to your environment or .env file."
        )

    primary_model = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct:free")
    backup_model = os.getenv("OPENROUTER_MODEL_BACKUP", "nvidia/nemotron-3-ultra-550b-a55b:free")

    # Try primary model first
    try:
        return _call_model(primary_model, prompt, api_key)
    except Exception as primary_err:
        print(f"⚠️  Primary model ({primary_model}) failed: {primary_err}")

    # Fall back to backup model
    try:
        print(f"🔄 Falling back to backup model: {backup_model}")
        return _call_model(backup_model, prompt, api_key)
    except Exception as backup_err:
        raise RuntimeError(
            f"Both models failed. Primary ({primary_model}): {primary_err}. "
            f"Backup ({backup_model}): {backup_err}"
        )


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

    IMPORTANT - Skill Normalization Rules:
    - Use the full canonical name for every skill (no abbreviations).
    - Examples: "JS" → "JavaScript", "TS" → "TypeScript", "Py" → "Python",
      "Postgres" → "PostgreSQL", "K8s" → "Kubernetes", "ML" → "Machine Learning",
      "NLP" → "Natural Language Processing", "CV" → "Computer Vision",
      "Go" or "Golang" → "Go", "ReactJS" → "React", "VueJS" → "Vue.js",
      "NodeJS" → "Node.js", "REST" → "REST API", "gRPC" stays "gRPC".
    - Use consistent capitalization (e.g. "JavaScript" not "javascript").
    - Deduplicate skills (no repeats).

    CV Text:
    {cv_text}
    """

    result = call_ai(prompt)
    result = result.replace("```json", "").replace("```", "").strip()
    return json.loads(result)


def save_candidates(candidate_data: dict) -> dict:
    """Insert or update a candidate record in `data/candidates.json` AND ChromaDB."""
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

    # --- NEW: also save into ChromaDB ---
    skills_text = ", ".join(candidate_data.get("skills", []))
    document_text = f"{candidate_data.get('summary', '')} Skills: {skills_text}"

    get_candidates_collection().upsert(
        ids=[str(candidate_data["id"])],
        documents=[document_text],
        metadatas=[{
            "name": candidate_data.get("name", ""),
            "experience_years": candidate_data.get("experience_years", 0),
            "skills": skills_text
        }]
    )

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

    skills_text = ", ".join(job_data.get("required_skills", []))
    document_text = f"{job_data.get('title', '')}. {job_data.get('summary', '')} Required Skills: {skills_text}"

    get_jobs_collection().upsert(
        ids=[str(job_data["id"])],
        documents= [document_text],
        metadatas = [{
            "title": job_data.get("title",""),
            "required_skills": skills_text
        }]
    )
    
    return job_data

def match_candidates(job_id: int):
    # ── STEP 1: Load the job from JSON ──
    # Same as before — read jobs.json and find the job by its ID.
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

    # ── STEP 2: Build the query text ──
    # We reconstruct the SAME text format used in save_job() so the
    # embedding ChromaDB generates for the query matches the space it
    # stored candidate documents in.
    job_skills_text = ", ".join(job.get("required_skills", []))
    job_query_text = (
        f"{job.get('title', '')}. {job.get('summary', '')} "
        f"Required Skills: {job_skills_text}"
    )

    # ── STEP 3: Query ChromaDB for semantically similar candidates ──
    # ChromaDB embeds our query text and finds the closest candidate
    # vectors. We fetch 20 so we have a pool to re-rank, then trim to 10.
    # If ChromaDB is empty or errors, we fall back to semantic_scores = {}.
    semantic_scores = {}
    try:
        chroma_results = get_candidates_collection().query(
            query_texts=[job_query_text],
            n_results=20,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        chroma_results = None

    # ── STEP 4: Convert distances → similarity scores ──
    # ChromaDB returns cosine DISTANCE (0 = identical, 2 = opposite).
    # We convert to similarity: 1 - distance  →  0.0 (unrelated) to 1.0 (perfect).
    # We store this in a dict keyed by candidate ID for fast lookup later.
    if chroma_results and chroma_results.get("ids"):
        ids = chroma_results["ids"][0]
        distances = chroma_results["distances"][0]
        for cid, dist in zip(ids, distances):
            similarity = max(0.0, 1.0 - dist)  # clamp negative values to 0
            semantic_scores[cid] = similarity

    # ── STEP 5: Load candidates from JSON ──
    # We still need the JSON file because it holds the full candidate
    # record (name, skills list, experience_years) in a structured form.
    try:
        with open(candidates_path, "r", encoding="utf-8") as f:
            candidates = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        candidates = []

    # ── STEP 6: Score each candidate with a blended formula ──
    # Three components combined into one score:
    #   • Semantic similarity (0–50 pts)  — catches "Postgres" ≈ "PostgreSQL"
    #   • Exact skill matches (10 pts each) — rewards precise keyword hits
    #   • Experience years (5 pts each) — rewards seniority
    required_skills = set(job.get("required_skills", []))
    best_by_name = {}

    for candidate in candidates:
        if not candidate.get("name") or not isinstance(candidate.get("skills"), list):
            continue

        cand_id = str(candidate.get("id", ""))

        # Semantic score from ChromaDB (0.0–1.0  →  0–50 points)
        sem_sim = semantic_scores.get(cand_id, 0.0)
        semantic_points = sem_sim * 50

        # Exact skill overlap (same logic as before)
        cand_skills = set(candidate.get("skills", []))
        matching_skills = list(cand_skills & required_skills)
        exact_points = len(matching_skills) * 10

        # Experience bonus (same logic as before)
        exp_points = candidate.get("experience_years", 0) * 5

        # Combined total score
        total_score = semantic_points + exact_points + exp_points

        result = {
            "candidate": candidate,
            "score": round(total_score, 2),
            "semantic_similarity": round(sem_sim, 4),
            "matching_skills": matching_skills,
        }

        # Dedup by name — keep the highest-scoring entry per candidate
        name_key = candidate.get("name", "").strip().lower()
        existing = best_by_name.get(name_key)
        if existing is None or result["score"] > existing["score"]:
            best_by_name[name_key] = result

    # ── STEP 7: Sort by combined score and return top 20 ──
    # We now keep top 20 (instead of 10) so the LLM has a bigger pool to re-rank.
    results = list(best_by_name.values())
    results.sort(key=lambda x: x["score"], reverse=True)
    top_results = results[:20]

    # ── STEP 8: AI Re-Ranking + Explanation ──
    # Send the top 20 candidates + job to the LLM. It re-ranks them with
    # real understanding and returns a fit_score + explanation for each.
    # If the LLM call fails, we fall back to the vector+math scores.
    try:
        reranked = ai_rerank_candidates(job, top_results)
        if reranked:
            return reranked[:10]
    except Exception:
        pass

    return top_results[:10]


def ai_rerank_candidates(job: dict, candidates: list) -> list:
    """Send top candidates + job to the LLM for re-ranking + explanation.

    Returns the candidates re-ordered with an added 'ai_explanation' and
    'ai_fit_score' field on each result.
    """
    job_title = job.get("title", "")
    job_summary = job.get("summary", "")
    job_skills = ", ".join(job.get("required_skills", []))
    min_exp = job.get("min_experience_years", 0)

    # Build a compact candidate list for the prompt
    cand_lines = []
    for i, r in enumerate(candidates):
        c = r["candidate"]
        skills = ", ".join(c.get("skills", []))
        exp = c.get("experience_years", 0)
        name = c.get("name", "")
        cand_lines.append(
            f"{i+1}. Name: {name} | Skills: {skills} | Experience: {exp} yrs | "
            f"Summary: {c.get('summary', '')}"
        )
    cand_block = "\n".join(cand_lines)

    prompt = f"""
    You are an expert technical recruiter. Re-rank these candidates for the job below.

    JOB:
    Title: {job_title}
    Summary: {job_summary}
    Required Skills: {job_skills}
    Minimum Experience: {min_exp} years

    CANDIDATES:
    {cand_block}

    Return ONLY a valid JSON array (no markdown, no extra text) with exactly 10 objects,
    ordered from best fit to worst fit. Each object must have:
    {{
        "name": "candidate name (exactly as shown above)",
        "ai_fit_score": 0-100,
        "ai_explanation": "one sentence explaining why this candidate fits or doesn't fit"
    }}

    Scoring guidance:
    - 90-100: Perfect match — has all required skills + meets experience
    - 70-89:  Strong match — has most required skills, close experience
    - 50-69:  Partial match — has some required skills
    - 0-49:   Weak match — missing key required skills
    """

    result = call_ai(prompt)
    result = result.replace("```json", "").replace("```", "").strip()

    # The LLM returns a JSON array of {name, ai_fit_score, ai_explanation}
    ai_ranking = json.loads(result)

    # Build a lookup: candidate name → ai data
    ai_by_name = {}
    for item in ai_ranking:
        name_key = item.get("name", "").strip().lower()
        ai_by_name[name_key] = item

    # Merge AI data back into our result objects, preserving original data
    merged = []
    for r in candidates:
        c = r["candidate"]
        name_key = c.get("name", "").strip().lower()
        ai_data = ai_by_name.get(name_key, {})

        merged.append({
            "candidate": c,
            "score": r.get("score", 0),
            "semantic_similarity": r.get("semantic_similarity", 0),
            "matching_skills": r.get("matching_skills", []),
            "ai_fit_score": ai_data.get("ai_fit_score", 0),
            "ai_explanation": ai_data.get("ai_explanation", ""),
        })

    # Sort by AI fit score (best first)
    merged.sort(key=lambda x: x.get("ai_fit_score", 0), reverse=True)
    return merged


def extract_job_data(job_text: str) -> dict:
    prompt = f"""
    Extract structured information from this job description.
    Return only a valid JSON object, no markdown, nothing else:
    {{
        "title": "job title",
        "required_skills": ["skill1", "skill2"],
        "min_experience_years": 2,
        "summary": "brief role summary"
    }}

    IMPORTANT - Skill Normalization Rules:
    - Use the full canonical name for every skill (no abbreviations).
    - Examples: "JS" → "JavaScript", "TS" → "TypeScript", "Py" → "Python",
      "Postgres" → "PostgreSQL", "K8s" → "Kubernetes", "ML" → "Machine Learning",
      "NLP" → "Natural Language Processing", "CV" → "Computer Vision",
      "Go" or "Golang" → "Go", "ReactJS" → "React", "VueJS" → "Vue.js",
      "NodeJS" → "Node.js", "REST" → "REST API", "gRPC" stays "gRPC".
    - Use consistent capitalization (e.g. "JavaScript" not "javascript").
    - Deduplicate skills (no repeats).

    Job Description:
    {job_text}
    """
    result = call_ai(prompt)
    result = result.replace("```json", "").replace("```", "").strip()
    return json.loads(result)    

