from fastapi import APIRouter, UploadFile, File, Body
from pydantic import BaseModel
from app.services import extract_cv_data, save_candidates, save_job, match_candidates, extract_job_data
from utils.pdf_parser import extract_text_from_pdf
router = APIRouter()

class CVInput(BaseModel):
    cv_text: str

class JobInput(BaseModel):
    title: str
    description: str
    required_skills: list

class JobTextInput(BaseModel):
    job_text: str

@router.post("/upload-cv")
def upload_cv(data: CVInput):
    extracted = extract_cv_data(data.cv_text)
    saved = save_candidates(extracted)
    return {"message": "CV saved", "candidate": saved}

@router.post("/create-job")
def create_job(data: JobInput):
    job = save_job(data.dict())
    return {"message": "Job created", "job": job}

@router.post("/upload-cv-pdf")
async def upload_cv_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    with open("temp_cv.pdf", "wb") as f:
        f.write(contents)
    text = extract_text_from_pdf("temp_cv.pdf")
    extracted = extract_cv_data(text)
    saved = save_candidates(extracted)
    return {"message": "CV saved", "candidate": saved}

@router.post("/upload-job-pdf")
async def upload_job_pdf(file: UploadFile = File(...)):
    contents = await file.read()              # ← ADD THIS
    with open("temp_job.pdf", "wb") as f:     # ← ADD THIS
        f.write(contents) 
    text = extract_text_from_pdf("temp_job.pdf")  
    job_data = extract_job_data(text)
    saved = save_job(job_data)
    return {"message": "Job saved", "job": saved}

@router.get("/matches/{job_id}")
def get_matches(job_id: int):
    matches = match_candidates(job_id)
    return {"job_id": job_id, "matches": matches}

class JobtextInput(BaseModel):
    job_text: str

@router.post("/upload-job")
async def upload_job(job_text: str = Body(..., media_type="text/plain")):
    extracted = extract_job_data(job_text)
    extracted["raw_text"] = job_text
    saved = save_job(extracted)
    return {"message": "Job saved", "job": saved}