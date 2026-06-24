import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "neuroguard.db")

def migrate():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add columns to users
        print("Adding risk_level to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN risk_level INTEGER DEFAULT 0;")
        print("Adding watchlist_reason to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN watchlist_reason VARCHAR(255);")
        print("Adding zone_access_level to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN zone_access_level VARCHAR(50) DEFAULT 'public';")
        
        # Add column to events
        print("Adding threat_score to events...")
        cursor.execute("ALTER TABLE events ADD COLUMN threat_score INTEGER DEFAULT 0;")
        
        conn.commit()
        print("Migration successful.")
    except sqlite3.OperationalError as e:
        print(f"Migration error (columns might already exist): {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
