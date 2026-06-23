import sys
from backend.database.session import SessionLocal
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE events ADD COLUMN threat_level VARCHAR(20) NOT NULL DEFAULT 'green'"))
    except: pass
    try:
        db.execute(text("ALTER TABLE events ADD COLUMN threat_type VARCHAR(50) NOT NULL DEFAULT 'none'"))
    except: pass
    try:
        db.execute(text("ALTER TABLE events ADD COLUMN threat_confidence FLOAT NOT NULL DEFAULT 0.0"))
    except: pass
    try:
        db.execute(text("ALTER TABLE events ADD COLUMN threat_persistence INTEGER NOT NULL DEFAULT 0"))
    except: pass
    
    try:
        db.commit()
        print("Database schema successfully migrated for Threat Intelligence!")
    except Exception as e:
        print("Migration failed:", str(e))
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
