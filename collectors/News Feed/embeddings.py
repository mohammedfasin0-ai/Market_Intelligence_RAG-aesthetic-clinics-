from sentence_transformers import SentenceTransformer
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

def embeddings():
    
    model = SentenceTransformer("all-MiniLM-L6-v2")  # downloads once, then runs locally, free forever
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    CHUNK_SIZE = 180
    OVERLAP = 30

    def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
        words = text.split()
        if len(words) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunks.append(" ".join(words[start:end]))
            start += chunk_size - overlap
        return chunks

    def embed_batch(texts):
        vectors = model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def process_pending_items(batch_size=50):
        result = supabase.table("content_items").select("*").eq("embedded", False).limit(batch_size).execute()
        items = result.data

        if not items:
            print("Nothing to embed.")
            return

        for item in items:
            chunks = chunk_text(item["text_for_embedding"])
            vectors = embed_batch(chunks)

            rows = [
                {
                    "content_item_id": item["id"],
                    "chunk_text": chunk,
                    "chunk_index": i,
                    "embedding": vector
                }
                for i, (chunk, vector) in enumerate(zip(chunks, vectors))
            ]

            supabase.table("embeddings").insert(rows).execute()
            supabase.table("content_items").update({"embedded": True}).eq("id", item["id"]).execute()
            print(f"Embedded content_item {item['id']} ({len(chunks)} chunks)")

    if __name__ == "__main__":
        while True:
            remaining = supabase.table("content_items").select("id").eq("embedded", False).limit(1).execute()
            if not remaining.data:
                print("All done.")
                break
            process_pending_items(batch_size=50)

if __name__ == "__main__":
    embeddings()