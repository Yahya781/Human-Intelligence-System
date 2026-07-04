from fastapi import APIRouter
from pydantic import BaseModel
from app.services import extract_cv_data, save_candidates, save_job, match_candidates

router = APIRouter()

class CVInput(BaseModel):
    cv_text: str

class JobInput(BaseModel):
    title: str
    description: str
    required_skills: list

@router.post("/upload-cv")
def upload_cv(data: CVInput):
    extracted = extract_cv_data(data.cv_text)
    saved = save_candidates(extracted)
    return {"message": "CV saved", "candidate": saved}

@router.post("/create-job")
def create_job(data: JobInput):
    job = save_job(data.dict())
    return {"message": "Job created", "job": job}

@router.get("/get-matches/{job_id}")
def get_matches(job_id: int):
    matches = match_candidates(job_id)
    return {"matches": matches}