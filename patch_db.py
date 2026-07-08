from sqlalchemy import create_engine, text
import os

db_url = 'postgresql://postgres.yrrazxpzozlbbsgiwwqf:CpFZIHSYonBVlezI@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres'
engine = create_engine(db_url)

with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE events ALTER COLUMN cnn_macs TYPE BIGINT;'))
        conn.execute(text('ALTER TABLE events ALTER COLUMN snn_spikes_ac TYPE BIGINT;'))
        conn.commit()
        print("Successfully altered cnn_macs and snn_spikes_ac to BIGINT.")
    except Exception as e:
        print(f"Error altering columns: {e}")
