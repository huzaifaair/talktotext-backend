TalkToText Pro - AI Meeting Notes Backend

Flask + Celery backend for TalkToText Pro, an AI-powered meeting transcription and summarization tool.
Handles file uploads, transcription, AI-based note generation, and export in multiple formats.

🚀 Features

Audio/Video Uploads: Supports MP3, MP4, WAV, and more

Background Processing: Celery + Redis for scalable task handling

AI-Powered Summarization: Generates structured notes with summaries, key points, and sentiment

Multi-language Support: Automatic language detection and translation

Download Options: Export notes as PDF or DOCX

User Authentication: Secure JWT-based auth system

History Tracking: Retrieve and manage user’s processed notes

🛠 Tech Stack

Framework: Flask

Task Queue: Celery + Redis

Database: MongoDB

Auth: JWT (python-jose)

File Handling: MoviePy for audio extraction

Export: FPDF + python-docx

📋 Prerequisites

Python 3.10+

Redis (running locally or cloud)

MongoDB (Atlas or local instance)

🚀 Quick Start
1. Clone and Install
git clone <repository-url>
cd talktotext-backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

2. Environment Setup

Create a .env file:

FLASK_ENV=production
PORT=8000

# --- Database ---
MONGO_URI=mongodb+srv://huzaifamustafadev1727_db_user:MhM16290%40101@talktotext.g3ekjqz.mongodb.net/talktotext?retryWrites=true&w=majority&appName=talktotext

# --- Security ---
JWT_SECRET=SuperMhM16290@1Security01Key   

# --- File storage ---
UPLOAD_FOLDER=./storage/uploads

# --- LLM (Groq) ---
LLM_PROVIDER=groq
LLM_API_KEY=____

# --- Speech-to-Text (AssemblyAI) ---
SPEECH_PROVIDER=assemblyai
SPEECH_API_KEY=_____

# --- Redis (for Celery) ---
REDIS_URL=redis://127.0.0.1:6379/0


3. Run the Services
Start Flask app:
python run.py

Start Celery worker:
celery -A core.celery_worker.celery worker --pool=solo -l info

📚 API Endpoints
🔐 Authentication
POST /auth/register
POST /auth/login

📂 Upload & Processing
POST /api/upload          # Upload file
GET  /api/status/<id>     # Check status
GET  /api/notes/<id>      # Fetch processed note
GET  /api/history         # User history

📥 Download
GET /api/download/pdf/<id>
GET /api/download/docx/<id>

🧪 Testing

Use Postman or cURL:

# Upload
curl -X POST http://localhost:8000/api/upload -F "file=@meeting.mp3" -H "Authorization: Bearer <token>"

# Check Status
curl http://localhost:8000/api/status/<upload_id>

🚀 Deployment
Railway (Recommended)

Push backend to GitHub

Connect Railway project

Add Environment Variables in Railway:

JWT_SECRET, MONGO_URI, REDIS_URL

Deploy 🚀

🐛 Known Issues

PDF Export: Unicode text (Urdu, Arabic, Chinese) may not render correctly in some environments.
👉 Workaround: DOCX export is always available.

🤝 Contributing

Fork the repo

Create a feature branch: git checkout -b feature/amazing-feature

Commit changes: git commit -m "Added amazing feature"

Push branch: git push origin feature/amazing-feature

Open PR

📄 License

This project is licensed under the MIT License.

🔗 Related Repos

Frontend (Next.js)

Backend (Flask)
