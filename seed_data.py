import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models import Event, User, Base
import os

db_url = os.environ.get('NEUROGUARD_DB_URL', 'postgresql://postgres:postgres@localhost:5432/postgres')
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

def seed_database():
    db = SessionLocal()
    
    print("Deleting old events...")
    db.query(Event).delete()
    db.commit()

    print("Creating sample users...")
    # Make sure we have some users
    employee_names = ["John Doe", "Jane Smith", "Alice Johnson", "Bob Williams", "Charlie Brown", "Diana Prince", "Bruce Wayne", "Clark Kent"]
    for i, name in enumerate(employee_names):
        if not db.query(User).filter(User.name == name).first():
            user = User(
                name=name,
                employee_id=f"EMP{i:03d}",
                department=random.choice(["Engineering", "Security", "HR", "Marketing"]),
                role="employee"
            )
            db.add(user)
    db.commit()
    
    users = db.query(User).all()
    user_ids = [u.id for u in users]
    
    print("Seeding 1000 events over the past 7 days...")
    events = []
    
    now = datetime.utcnow()
    
    # Generate 1000 events
    for _ in range(1000):
        # 80% recognized, 20% strangers
        is_recognized = random.random() < 0.8
        
        # Random time within the last 7 days (weighted towards daytime hours)
        days_ago = random.randint(0, 6)
        
        # More traffic during business hours (8 AM to 6 PM)
        is_business_hour = random.random() < 0.7
        if is_business_hour:
            hour = random.randint(8, 18)
        else:
            hour = random.choice([0, 1, 2, 3, 4, 5, 6, 7, 19, 20, 21, 22, 23])
            
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        
        timestamp = now - timedelta(days=days_ago)
        timestamp = timestamp.replace(hour=hour, minute=minute, second=second)
        
        if is_recognized:
            user = random.choice(users)
            event = Event(
                user_id=user.id,
                event_type="recognized",
                person_name=user.name,
                confidence=random.uniform(0.7, 0.99),
                snn_score=random.uniform(0.6, 0.95),
                cosine_score=random.uniform(0.6, 0.95),
                threat_level="green",
                threat_type="none",
                threat_confidence=0.0,
                threat_persistence=0,
                threat_score=0,
                timestamp=timestamp
            )
        else:
            # 10% of strangers are actually threats
            is_threat = random.random() < 0.1
            threat_level = random.choice(["orange", "red"]) if is_threat else "yellow"
            threat_type = random.choice(["knife", "gun", "unauthorized"]) if is_threat else "none"
            threat_score = random.randint(50, 100) if is_threat else 0
            
            event = Event(
                user_id=None,
                event_type="stranger",
                person_name=None,
                confidence=random.uniform(0.4, 0.6),
                snn_score=random.uniform(0.2, 0.5),
                cosine_score=random.uniform(0.2, 0.5),
                threat_level=threat_level,
                threat_type=threat_type,
                threat_confidence=0.9 if is_threat else 0.0,
                threat_persistence=3 if is_threat else 0,
                threat_score=threat_score,
                timestamp=timestamp
            )
            
        events.append(event)
        
    # Standard insert handles SQLAlchemy defaults properly
    db.add_all(events)
    db.commit()
    print("Successfully seeded 1000 events!")
    db.close()

if __name__ == "__main__":
    seed_database()
