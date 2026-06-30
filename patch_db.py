from sqlalchemy import create_engine, text
import os

db_url = os.environ.get('NEUROGUARD_DB_URL', 'postgresql://postgres:postgres@localhost:5432/postgres')
engine = create_engine(db_url)

with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE events ADD COLUMN IF NOT EXISTS video_path VARCHAR(500);'))
        conn.commit()
        print("Successfully added video_path column.")
    except Exception as e:
        print(f"Error adding video_path: {e}")
