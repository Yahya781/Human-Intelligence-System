"""
Rebuild ChromaDB collections from the JSON data files.
Run this after manually editing candidates.json or jobs.json.
"""
import os
import json
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

chroma_client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_data"))
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Delete and recreate collections (clean slate)
try:
    chroma_client.delete_collection("candidates")
    chroma_client.delete_collection("jobs")
except Exception:
    pass

candidates_collection = chroma_client.get_or_create_collection(
    name="candidates", embedding_function=embedding_fn
)
jobs_collection = chroma_client.get_or_create_collection(
    name="jobs", embedding_function=embedding_fn
)

# ── Load candidates into ChromaDB ──
with open(os.path.join(BASE_DIR, "data", "candidates.json"), "r", encoding="utf-8") as f:
    candidates = json.load(f)

if candidates:
    ids = [str(c["id"]) for c in candidates]
    documents = [
        f"{c.get('summary', '')} Skills: {', '.join(c.get('skills', []))}"
        for c in candidates
    ]
    metadatas = [
        {
            "name": c.get("name", ""),
            "experience_years": c.get("experience_years", 0),
            "skills": ", ".join(c.get("skills", [])),
        }
        for c in candidates
    ]
    candidates_collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

print(f"✅ Loaded {len(candidates)} candidates into ChromaDB")

# ── Load jobs into ChromaDB ──
with open(os.path.join(BASE_DIR, "data", "jobs.json"), "r", encoding="utf-8") as f:
    jobs = json.load(f)

if jobs:
    ids = [str(j["id"]) for j in jobs]
    documents = [
        f"{j.get('title', '')}. {j.get('summary', '')} Required Skills: {', '.join(j.get('required_skills', []))}"
        for j in jobs
    ]
    metadatas = [
        {
            "title": j.get("title", ""),
            "required_skills": ", ".join(j.get("required_skills", [])),
        }
        for j in jobs
    ]
    jobs_collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

print(f"✅ Loaded {len(jobs)} jobs into ChromaDB")
print("\nDone! ChromaDB is now in sync with JSON files.")
