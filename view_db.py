import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="chroma_data")

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-V2"
)

candidates_collection = client.get_or_create_collection("candidates", embedding_function= embedding_fn)
jobs_collection = client.get_or_create_collection("jobs", embedding_function= embedding_fn)

print("Candidates:")
print(candidates_collection.get())

print("\njobs:")
print(jobs_collection.get())