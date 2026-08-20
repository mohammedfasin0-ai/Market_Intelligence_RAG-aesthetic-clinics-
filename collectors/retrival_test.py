from sentence_transformers import SentenceTransformer
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

model = SentenceTransformer("all-MiniLM-L6-v2")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

question = "What are people saying about bad experiences with fillers?"
question_vector = model.encode([question], normalize_embeddings=True)[0].tolist()

result = supabase.rpc('match_embeddings', {
    'query_embedding': question_vector,
    'match_count': 5
}).execute()

for row in result.data:
    print(row['distance'], '-', row['chunk_text'][:500])