import os
import requests
import time
from datetime import datetime

from core.providers import call_llm
from core.utils import extract_audio_from_video, translate_text, optimize_for_tokens
from config import Config
from models.mongo_models import uploads, notes


ASSEMBLY_HEADERS = {"authorization": Config.SPEECH_API_KEY}


def upload_to_assemblyai(file_path: str) -> str:
    """
    Uploads local audio/video file to AssemblyAI and returns upload_url.
    If file_path is already a URL, just return it.
    """
    if file_path.startswith("http://") or file_path.startswith("https://"):
        # Already a remote URL (Zoom/Meet/AssemblyAI etc.)
        return file_path

    headers = {"authorization": Config.SPEECH_API_KEY}
    with open(file_path, "rb") as f:
        response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            data=f,
            timeout=120
        )
        response.raise_for_status()
        return response.json()["upload_url"]


# --- Transcribe when we already have an AssemblyAI upload_url ---
def transcribe_with_assemblyai_url(audio_url: str, language: str = "auto"):
    endpoint = "https://api.assemblyai.com/v2/transcript"
    json_data = {"audio_url": audio_url, "language_detection": True}
    if language and language != "auto":
        json_data["language_code"] = language

    r = requests.post(endpoint, headers=ASSEMBLY_HEADERS, json=json_data, timeout=60)
    r.raise_for_status()
    transcript_id = r.json()["id"]

    status_endpoint = f"{endpoint}/{transcript_id}"
    while True:
        res = requests.get(status_endpoint, headers=ASSEMBLY_HEADERS, timeout=60)
        res.raise_for_status()
        data = res.json()
        if data["status"] == "completed":
            return data["text"], data.get("language_code", "auto")
        elif data["status"] == "error":
            raise RuntimeError(f"AssemblyAI error: {data['error']}")
        time.sleep(2)


# --- Fallback (mock/local) ---
def transcribe_local(filepath):
    return "Dummy transcript (replace with actual STT)", "en"


def transcribe(file_or_url: str, language: str = None, is_url: bool = False):
    """
    Unified transcription handler (local file, remote URL, or pre-uploaded AssemblyAI URL).
    """
    # 1. Get upload_url (skip if already URL)
    upload_url = upload_to_assemblyai(file_or_url)

    # 2. Request transcription
    endpoint = "https://api.assemblyai.com/v2/transcript"
    headers = {"authorization": Config.SPEECH_API_KEY}
    json_data = {"audio_url": upload_url, "language_detection": True}
    if language and language != "auto":
        json_data["language_code"] = language

    transcript_res = requests.post(endpoint, headers=headers, json=json_data, timeout=30)
    transcript_res.raise_for_status()
    transcript_id = transcript_res.json()["id"]

    # 3. Poll until done
    status_endpoint = f"{endpoint}/{transcript_id}"
    while True:
        poll_res = requests.get(status_endpoint, headers=headers, timeout=30)
        poll_res.raise_for_status()
        data = poll_res.json()
        if data["status"] == "completed":
            return data["text"], data.get("language_code", "auto")
        elif data["status"] == "error":
            raise RuntimeError(f"AssemblyAI error: {data['error']}")
        time.sleep(2)


# --- Clean transcript ---
def clean_text(text):
    if not text:
        return text
    for w in [" um ", " uh ", " you know ", " like "]:
        text = text.replace(w, " ")
    return " ".join(text.split())


# --- Summarization ---
def generate_notes(transcript):
    prompt = f"""You are an advanced multilingual meeting summarizer.
The transcript may not always be in English, but the final notes must be in **English**.

Please return the meeting summary STRICTLY in valid GitHub-flavored Markdown with this structure:

## Abstract Summary
- 3–4 lines abstract summarizing the overall meeting.

## Key Points
- Bullet points of important highlights.

## Action Items
1. Numbered list of action items (Who – What – By When).

## Sentiment
- Short paragraph describing the meeting tone.

Important formatting rules:
- Use `##` for section headings (not bold or underline).
- Use `-` for bullets under Key Points.
- Use `1. 2. 3.` style for Action Items.
- Do not include anything outside these sections.
- Keep the style professional and concise.

Transcript extract:
{transcript}
"""
    return call_llm(prompt)


# --- Progress helper ---
def set_progress(upload_id, stage, percent):
    try:
        uploads.update_one(
            {"_id": upload_id},
            {"$set": {
                "status": stage,
                "progress": {"stage": stage, "percent": percent}
            }}
        )
    except Exception:
        pass


# --- Main pipeline ---
def process_upload(upload_id, file_path_or_url, user_id, language="auto", is_url=False):
    """
    file_path_or_url -> can be:
        - local audio file
        - local video file
        - external meeting URL (e.g. YouTube, Zoom recording link)
    """
    try:
        set_progress(upload_id, "processing", 5)

        # 1. Handle MP4 (extract first 2 minutes of audio)
        if not is_url and file_path_or_url.lower().endswith(".mp4"):
            set_progress(upload_id, "extracting", 10)
            audio_path = file_path_or_url.rsplit(".", 1)[0] + "_2min.mp3"
            file_path_or_url = extract_audio_from_video(file_path_or_url, audio_path, duration=120)
            set_progress(upload_id, "extracted", 20)

        # 2. Transcribe
        set_progress(upload_id, "transcribing", 30)
        transcript, detected_lang = transcribe(file_path_or_url, is_url=is_url, language=language)
        set_progress(upload_id, "transcribed", 45)

        # 3. Translate if not English
        if detected_lang.lower() != "en":
            set_progress(upload_id, "translating", 55)
            translated = translate_text(transcript, src=detected_lang, target="en")
            set_progress(upload_id, "translated", 65)
        else:
            translated = transcript

        # 4. Clean + optimize
        cleaned = clean_text(translated)
        cleaned = optimize_for_tokens(cleaned, max_tokens=3000)
        set_progress(upload_id, "optimized", 75)

        # 5. Summarize
        set_progress(upload_id, "summarizing", 85)
        notes_text = generate_notes(cleaned)
        set_progress(upload_id, "summarized", 95)

        # 6. Save DB
        note_doc = {
            "user_id": user_id,
            "upload_id": upload_id,
            "raw_transcript": transcript,
            "translated_transcript": translated if translated != transcript else None,
            "cleaned_transcript": cleaned,
            "final_notes": notes_text,
            "detected_language": detected_lang,
            "created_at": datetime.utcnow()
        }
        res = notes.insert_one(note_doc)

        uploads.update_one(
            {"_id": upload_id},
            {"$set": {
                "status": "done",
                "note_id": str(res.inserted_id),   # 👈 yaha bhi string
                "progress": {"stage": "done", "percent": 100}
            }}
        )
        return {"note_id": str(res.inserted_id)}

    except Exception as e:
        uploads.update_one(
            {"_id": upload_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise
