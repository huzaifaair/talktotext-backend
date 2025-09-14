import os
import requests
import time
from datetime import datetime

from core.providers import call_llm
from core.utils import extract_audio_from_video, translate_text, optimize_for_tokens
from config import Config
from models.mongo_models import uploads, notes


# --- AssemblyAI transcription with auto language detection ---
def transcribe_with_assemblyai(filepath):
    headers = {"authorization": Config.SPEECH_API_KEY}

    # Step 1: Upload file
    with open(filepath, "rb") as f:
        upload_url = "https://api.assemblyai.com/v2/upload"
        r = requests.post(upload_url, headers=headers, data=f, timeout=120)
        r.raise_for_status()
        audio_url = r.json()["upload_url"]

    # Step 2: Request transcription (auto-detect language)
    endpoint = "https://api.assemblyai.com/v2/transcript"
    json_data = {"audio_url": audio_url, "language_detection": True}
    r = requests.post(endpoint, headers=headers, json=json_data, timeout=30)
    r.raise_for_status()
    transcript_id = r.json()["id"]

    # Step 3: Poll until transcription is complete
    status_endpoint = f"{endpoint}/{transcript_id}"
    while True:
        res = requests.get(status_endpoint, headers=headers, timeout=30)
        res.raise_for_status()
        data = res.json()
        if data["status"] == "completed":
            transcript_text = data["text"]
            detected_lang = data.get("language_code", "auto")
            return transcript_text, detected_lang
        elif data["status"] == "error":
            raise RuntimeError(f"AssemblyAI error: {data['error']}")
        time.sleep(2)


# --- Fallback (mock/local) ---
def transcribe_local(filepath):
    return "Dummy transcript (replace with actual STT)", "en"


# --- Wrapper ---
def transcribe(filepath):
    if Config.SPEECH_PROVIDER == "assemblyai":
        return transcribe_with_assemblyai(filepath)
    else:
        return transcribe_local(filepath)


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
def process_upload(upload_id, file_path, user_id, language="auto"):
    try:
        set_progress(upload_id, "processing", 5)

        # 1. Handle MP4 → extract first 2 minutes
        if file_path.lower().endswith(".mp4"):
            set_progress(upload_id, "extracting", 10)
            audio_path = file_path.rsplit(".", 1)[0] + "_2min.mp3"
            file_path = extract_audio_from_video(file_path, audio_path, duration=120)
            set_progress(upload_id, "extracted", 20)

        # 2. Transcribe (AssemblyAI auto-detect)
        set_progress(upload_id, "transcribing", 30)
        transcript, detected_lang = transcribe(file_path)
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
            {"$set": {"status": "done", "note_id": res.inserted_id,
                      "progress": {"stage": "done", "percent": 100}}}
        )
        return res.inserted_id

    except Exception as e:
        uploads.update_one(
            {"_id": upload_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise
