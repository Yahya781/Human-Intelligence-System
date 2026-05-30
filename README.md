# Human Intelligence System

An AI-powered talent screening and matching project that extracts structured information from CVs, stores candidate and job records, and ranks candidates against a job's required skills.

## What it does

- Extracts candidate details from resume text with an LLM
- Saves candidates and jobs into local JSON files
- Matches candidates to jobs by skill overlap and experience
- Produces simple scored recommendations for shortlisting

## Project structure

- `app/main.py` runs a sample extraction, save, and matching flow
- `app/services.py` contains the core AI, save, and matching logic
- `models/candidate.py` is reserved for candidate data structures
- `utils/pdf_parser.py` is reserved for parsing PDF resumes

## Setup

1. Create and activate your Python environment.
2. Install the required packages.
3. Add your OpenRouter key and model in `.env`.

Example `.env` values:

```env
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=google/gemma-4-31b-it:free
```

## Run

```powershell
python app/main.py
```

Or run it as an API app with Uvicorn:

```powershell
python -m uvicorn app.main:app --reload
```

## Notes

- Candidate records are stored in `data/candidates.json`
- Job records are stored in `data/jobs.json`
- Matching results are ranked by experience and matching skills