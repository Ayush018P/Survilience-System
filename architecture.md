# NeuroGuard AI - Architecture Design

## System Overview

NeuroGuard AI follows a decoupled microservices-style architecture, combining an async Python backend with a reactive JavaScript frontend. State and events are managed between services using Redis.

## AI Pipeline Flow

The AI pipeline is optimized for edge deployment, designed to process video frames in real-time.

1.  **Frame Capture:** The React frontend captures video via `getUserMedia`, draws to a hidden canvas, and transmits base64 JPEG frames over WebSockets.
2.  **Detection (MTCNN):** The FastAPI backend receives the frame. MTCNN detects bounding boxes and aligns the face crops.
3.  **Embedding (ResNet):** `InceptionResnetV1` extracts a robust 512-dimensional feature vector from the aligned face.
4.  **Spike Encoding:** The continuous 512-d vector is converted into a binary Poisson spike train over 10-20 time steps.
5.  **SNN Classification:** A 3-layer Leaky Integrate-and-Fire (LIF) network (`snntorch`) processes the spikes and outputs class probabilities.
6.  **Hybrid Decision Engine:** A weighted combination of the SNN probability and Cosine Similarity (against cached DB centroids) determines the final identity and confidence score.
7.  **Event Generation:** If confidence < threshold, it is flagged as a "Stranger". The event is saved to SQLite and broadcasted via Redis Pub/Sub back to the frontend.

## Database Schema (SQLite)

-   **Users:** Stores identity metadata, role, and a reference to the initial profile photo.
-   **Embeddings:** Stores the raw 512-d vectors as serialized bytes (NumPy). Related to Users.
-   **Centroids:** Stores the aggregated mean embedding for rapid Cosine Similarity checks.
-   **Events:** Logs all detections (timestamp, identity, scores, and optionally a snapshot path for strangers).
-   **Models:** Tracks versions of the trained SNN, their accuracy, and the file path to the `.pt` checkpoint.

## Redis Usage Patterns

We use Redis for four distinct use cases:
1.  **High-Speed Cache:** Storing centroids in memory to prevent SQLite I/O bottlenecks during live 10 FPS surveillance processing.
2.  **Pub/Sub Event Bus:** Instantly routing "Stranger" alerts from the backend pipeline to the React Dashboard via WebSocket.
3.  **Task Queue Placeholder:** Queuing SNN retraining jobs (simulated in the current MVP, but ready for Celery/RQ integration).
4.  **JWT Blacklist:** Storing revoked tokens upon logout to ensure strict session termination.

## Deployment Topology (Render.com)

-   **Frontend:** Hosted on Render Static Site globally via CDN.
-   **Backend:** Hosted on a Render Web Service with a connected Persistent Disk (for SQLite db and snapshot images).
-   **Redis:** Hosted on Render Redis.

## Future Scaling Considerations

To evolve this MVP into an enterprise SaaS:
1.  Replace SQLite with PostgreSQL (Vector extensions like `pgvector` could replace the manual cosine loop).
2.  Move the AI Pipeline to a dedicated GPU worker service separate from the FastAPI web server.
3.  Implement Kafka/RabbitMQ instead of Redis for persistent event streams.
