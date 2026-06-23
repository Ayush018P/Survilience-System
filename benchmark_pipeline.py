"""
NeuroGuard AI - Local Pipeline Benchmark
=========================================
Runs the Hybrid CNN-SNN pipeline locally on webcam feed to validate
telemetry, latency, and stability score calculations without needing the frontend.
"""

import asyncio
import cv2
import sys
import os

# Ensure backend module is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database.session import SessionLocal, create_tables
from backend.ai.pipeline import get_pipeline
from backend.database import crud
import numpy as np

async def main():
    print("Initializing Database...")
    create_tables()
    db = SessionLocal()
    
    # We need a dummy centroid to test Cosine Similarity
    # Check if we have any users, if not, create a dummy one
    users = crud.get_all_users(db)
    if not users:
        print("Creating dummy user for benchmark...")
        user = crud.create_user(db, name="Benchmark Subject", employee_id="BM-01", department="Test")
        # Dummy 512d vector
        dummy_vec = np.random.rand(512).astype(np.float32)
        # normalize it
        dummy_vec = dummy_vec / np.linalg.norm(dummy_vec)
        crud.store_embeddings_batch(db, user.id, [dummy_vec], dummy_vec)
        print("Dummy user created.")
    else:
        print(f"Found {len(users)} registered users.")

    print("\nInitializing AI Pipeline (Loading MTCNN, ResNet, SNN)...")
    pipeline = get_pipeline()
    pipeline.load_active_model(db)
    
    print("\nOpening Webcam...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
        
    print("\n" + "="*50)
    print("BENCHMARK STARTED. PRESS 'q' TO QUIT.")
    print("="*50 + "\n")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break
                
            frame_count += 1
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame
            results = await pipeline.process_frame_async(frame_rgb, db)
            
            # Draw and Print Metrics
            for r in results:
                print(f"Frame {frame_count}:")
                print(f"  Identity: {r.person_name} (Confidence: {r.confidence:.2f})")
                print(f"  Stability Score: {r.stability_score:.2f} | Identity Switch: {r.is_identity_switch}")
                print(f"  Latency - CNN: {r.cnn_latency_ms:.1f}ms | SNN: {r.snn_latency_ms:.1f}ms | Hybrid: {r.hybrid_latency_ms:.1f}ms")
                print(f"  Efficiency - MACs: {r.cnn_macs} | Spikes (ACs): {r.snn_spikes_ac}")
                print("-" * 50)
                
                # Draw on frame
                x1, y1, x2, y2 = r.bbox.x1, r.bbox.y1, r.bbox.x2, r.bbox.y2
                color = (0, 0, 255) if r.is_stranger else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{r.person_name} ({r.confidence:.2f})", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                            
            # Headless mode: skip cv2.imshow to prevent GUI errors
            # cv2.imshow('NeuroGuard Benchmark', frame)
            
            # Wait a short bit to yield control or check for exit if we had a window
            # but since we are headless, we can just run as fast as possible or sleep
            await asyncio.sleep(0.01)
                
    finally:
        cap.release()
        db.close()
        
if __name__ == "__main__":
    asyncio.run(main())
