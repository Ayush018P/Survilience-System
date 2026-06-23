import sys
from backend.database.session import SessionLocal
from backend.database import crud
from datetime import datetime, timedelta

from sqlalchemy import text
def test_events():
    db = SessionLocal()
    print("Total events in DB:", db.execute(text("SELECT COUNT(*) FROM events")).scalar())
    
    start_date = datetime.utcnow() - timedelta(days=7)
    events = crud.get_events(db, start_date=start_date)
    print("Events fetched by crud:", len(events))
    
    all_events = crud.get_events(db)
    print("Events fetched without start_date:", len(all_events))
    
if __name__ == "__main__":
    test_events()
