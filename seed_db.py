import datetime
import random
import numpy as np
import sys
import os

# Add backend to path so we can import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database.session import SessionLocal, create_tables
from backend.database import crud

def seed_data():
    create_tables()
    db = SessionLocal()
    try:
        print("Generating mock users...")
        users = []
        for i in range(1, 11):
            name = f"Employee {i}"
            user = crud.create_user(
                db, 
                name=name, 
                employee_id=f"EMP{1000+i}", 
                department=random.choice(["Engineering", "HR", "Security", "Operations"]),
                role="employee"
            )
            users.append(user)
            
            # Create mock embeddings
            vectors = np.random.rand(5, 512).astype(np.float32)
            centroid = np.mean(vectors, axis=0)
            centroid = centroid / np.linalg.norm(centroid)
            crud.store_embeddings_batch(db, user.id, vectors, centroid)
            
        print("Generating mock AI model record...")
        model = crud.create_model_record(
            db,
            version="1.0.0",
            accuracy=0.985,
            num_classes=10,
            num_epochs=50,
            checkpoint_path="models/test_model.pt",
            loss_final=0.015,
            training_duration_seconds=120.5
        )
        crud.set_active_model(db, model.id)
        
        print("Generating 500 mock events spanning the last 7 days...")
        now = datetime.datetime.utcnow()
        for i in range(500):
            # 80% recognized, 20% stranger
            is_recognized = random.random() < 0.8
            event_type = "recognized" if is_recognized else "stranger"
            
            # Spread over last 7 days, but weight heavily towards today
            days_ago = random.expovariate(1.0)
            if days_ago > 7: days_ago = random.uniform(0, 7)
            timestamp = now - datetime.timedelta(days=days_ago)
            
            person_name = None
            user_id = None
            if is_recognized:
                user = random.choice(users)
                person_name = user.name
                user_id = user.id
                
            confidence = random.uniform(0.70, 0.99) if is_recognized else random.uniform(0.1, 0.5)
            snn_score = random.uniform(0.6, 0.99) if is_recognized else random.uniform(0.0, 0.4)
            cosine_score = random.uniform(0.6, 0.99) if is_recognized else random.uniform(0.0, 0.4)
            
            event = crud.create_event(
                db,
                event_type=event_type,
                confidence=confidence,
                user_id=user_id,
                person_name=person_name,
                snn_score=snn_score,
                cosine_score=cosine_score
            )
            # Override timestamp
            event.timestamp = timestamp
            
        db.commit()
        print("Seed complete! You can now view the dashboard.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
