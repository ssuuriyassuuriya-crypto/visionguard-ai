# VisionGuard AI

VisionGuard AI is a lightweight safety-monitoring demo that analyzes uploaded images and videos using real YOLOv8 inference, calculates risk levels, and stores historical results in SQLite.

## Features
- Real object detection with Ultralytics YOLOv8n
- Image and video upload analysis
- Bounding boxes and confidence metrics
- Dynamic risk scoring and risk timeline for videos
- SQLite-backed history records
- Professional dark-mode dashboard UI

## Setup

### Backend
1. Open a terminal in the project root.
2. Create a virtual environment:
   python -m venv .venv
3. Activate it:
   .\.venv\Scripts\activate
4. Install dependencies:
   pip install -r backend/requirements.txt
5. Download YOLO model file into backend/models/yolov8n.pt
   - If the file is not present, the app will attempt to use Ultralytics to download it automatically.
6. Start the API:
   python backend/main.py

### Frontend
1. In a second terminal, go to frontend:
   cd frontend
2. Install dependencies:
   npm install
3. Start the Vite app:
   npm run dev

## Default config
- Backend: http://localhost:8000
- Frontend: http://localhost:5173

## Notes
The app is intentionally simple and focused on reliability for a Windows laptop environment.
