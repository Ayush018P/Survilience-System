import asyncio
import numpy as np
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal
from backend.database.models import Embedding, User
from backend.services.redis_service import redis_service

def normalize_db():
    db: Session = SessionLocal()
    users = db.query(User).all()
    print(f"Found {len(users)} users.")
    
    for user in users:
        print(f"Normalizing embeddings for {user.name}...")
        embeddings = db.query(Embedding).filter(Embedding.user_id == user.id, Embedding.is_centroid == 0).all()
        
        if not embeddings:
            continue
            
        vectors = []
        for emb in embeddings:
            vec = np.array(emb.vector, dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            # Update the DB record
            emb.vector = vec.tolist()
            vectors.append(vec)
            
        # Recompute centroid
        mean_embedding = np.mean(vectors, axis=0)
        norm = np.linalg.norm(mean_embedding)
        if norm > 0:
            mean_embedding = mean_embedding / norm
            
        # Update centroid
        centroid_emb = db.query(Embedding).filter(Embedding.user_id == user.id, Embedding.is_centroid == 1).first()
        if centroid_emb:
            centroid_emb.vector = mean_embedding.tolist()
        else:
            centroid_emb = Embedding(user_id=user.id, vector=mean_embedding.tolist(), is_centroid=1)
            db.add(centroid_emb)
            
    db.commit()
    print("Database normalized successfully.")

async def clear_redis():
    await redis_service.connect()
    await redis_service.invalidate_all_centroids()
    await redis_service.disconnect()
    print("Redis cache invalidated.")

if __name__ == "__main__":
    normalize_db()
    asyncio.run(clear_redis())
