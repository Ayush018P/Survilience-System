import sqlite3

def migrate():
    print("Starting DVR migration...")
    conn = sqlite3.connect("data/neuroguard.db")
    cursor = conn.cursor()
    
    try:
        # Check if video_path column exists
        cursor.execute("PRAGMA table_info(events)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "video_path" not in columns:
            cursor.execute("ALTER TABLE events ADD COLUMN video_path VARCHAR(500)")
            print("Successfully added 'video_path' column to 'events' table.")
        else:
            print("'video_path' column already exists.")
            
        conn.commit()
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
