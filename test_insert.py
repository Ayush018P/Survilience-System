import sys
from backend.database.session import SessionLocal
from backend.database import crud

def test_insert():
    db = SessionLocal()
    try:
        # Get first user from DB
        from backend.database.models import User
        user = db.query(User).first()
        user_id = user.id if user else None
        
        event = crud.create_event(
            db=db,
            event_type="recognized",
            confidence=0.99,
            user_id=user_id,
            person_name="Ayush Patel",
            snn_score=0.95,
            cosine_score=0.96,
            cnn_latency_ms=10.0,
            snn_latency_ms=2.0,
            hybrid_latency_ms=15.0,
            cnn_macs=1000,
            snn_spikes_ac=50,
            is_identity_switch=False,
            stability_score=0.9,
            snapshot_path=None
        )
        print("Success! Event inserted with ID:", event.id)
    except Exception as e:
        print("Error inserting event:", str(e))

if __name__ == "__main__":
    test_insert()
