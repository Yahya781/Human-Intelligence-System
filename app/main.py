from app.services import extract_cv_data, save_candidates, save_job, match_candidates
from fastapi import FastAPI
from app.routes import router

app = FastAPI()
app.include_router(router)

@app.get("/")
def home():
    return {"message": "AI Talent System running"}

CV_TEXT = """
John Doe
Software Engineer with 3 years experience.
Skills: Python, FastAPI, PostgreSQL, Docker
Worked at Tech Corp from 2021-2024
"""

JOB = {
    "title": "Python Backend Developer",
    "description": "Looking for Python developer with FastAPI experience to build REST APIs with PostgreSQL.",
    "required_skills": ["Python", "FastAPI", "PostgreSQL"],
}


def main():
    candidate = extract_cv_data(CV_TEXT)
    saved_candidate = save_candidates(candidate)
    print("Candidate saved:", saved_candidate)

    saved_job = save_job(JOB)
    print("Job saved:", saved_job)

    matches = match_candidates(saved_job["id"])
    for match in matches:
        candidate_name = match["candidate"].get("name", "Unknown")
        print(
            f"{candidate_name} - Score: {match['score']} - Matching Skills: {match['matching_skills']}"
        )


if __name__ == "__main__":
    main()
