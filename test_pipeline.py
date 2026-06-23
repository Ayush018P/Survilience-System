import asyncio
import cv2
import numpy as np
from backend.ai.pipeline import get_pipeline
from backend.database.session import SessionLocal

async def test():
    print("Testing pipeline...")
    pipeline = get_pipeline()
    # Create dummy frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    db = SessionLocal()
    try:
        results, threats = await pipeline.process_frame_async(frame, db)
        print("Results:", results)
        print("Threats:", threats)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test())
