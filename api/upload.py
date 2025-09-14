from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os, uuid, requests
from models.mongo_models import uploads
from datetime import datetime
from core.ai_pipeline import process_upload
from core.tasks import process_upload_task   # 🔹 Celery task import
from jose import jwt
from config import Config

bp = Blueprint('upload', __name__, url_prefix='/api')

ALLOWED = {"wav", "mp3", "mp4", "m4a"}

def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED

def get_user_from_auth():
    """
    Extract user_id from JWT token.
    If not logged in, fallback to demo_user (guest mode).
    """
    auth = request.headers.get("Authorization", "")
    if not auth:
        return "demo_user"
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
            return str(payload.get("sub", "demo_user"))
        except Exception:
            return "demo_user"
    return "demo_user"

def download_remote_file(url, out_path):
    """Download file from remote URL (Zoom/Meet etc)."""
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return out_path


@bp.route('/upload', methods=['POST'])
def upload_file():
    user_id = get_user_from_auth()  # 🔑 handles guest vs logged in
    f = request.files.get('file')
    url = request.form.get('url') or (request.json.get('url') if request.is_json else None)
    language = request.form.get('language') or request.args.get('language') or None
    background = request.form.get('background', "true").lower() != "false"

    # 🔹 New: extractDuration
    try:
        extract_duration = int(request.form.get("extractDuration") or request.json.get("extractDuration") if request.is_json else 0)
    except Exception:
        extract_duration = 0

    if not f and not url:
        return jsonify({"error": "file or url required (.mp3/.wav/.mp4/.m4a)"}), 400

    uid = str(uuid.uuid4())
    outdir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(outdir, exist_ok=True)

    # Save uploaded or remote file
    if f:
        if not allowed(f.filename):
            return jsonify({"error": "unsupported file type"}), 400
        fname = secure_filename(f.filename)
        path = os.path.join(outdir, f"{uid}_{fname}")
        f.save(path)
    else:
        ext = url.split('?')[0].split('.')[-1]
        if ext.lower() not in ALLOWED:
            ext = "mp4"
        path = os.path.join(outdir, f"{uid}_remote.{ext}")
        try:
            download_remote_file(url, path)
        except Exception as e:
            return jsonify({"error": f"download failed: {str(e)}"}), 400

    # Insert upload record (now includes extractDuration)
    up_doc = {
        "_id": uid,
        "user_id": user_id,  # 🔑 guest = demo_user
        "filename": os.path.basename(path),
        "path": path,
        "status": "uploaded",
        "created_at": datetime.utcnow(),
        "progress": {"stage": "uploaded", "percent": 0},
        "language": language or "auto",
        "extract_duration": extract_duration  # 🔹 saved here
    }
    uploads.insert_one(up_doc)

    # Background async via Celery
    if background:
        process_upload_task.delay(uid, path, user_id, language or "auto")
        return jsonify({"upload_id": uid}), 201
    else:
        note_id = process_upload(uid, path, user_id, language=language or "auto")
        return jsonify({
            "upload_id": uid,
            "note_id": str(note_id),
            "extract_duration": extract_duration
        }), 201


# 🔹 Status API
@bp.route('/status/<upload_id>', methods=['GET'])
def status(upload_id):
    u = uploads.find_one({"_id": upload_id}, {"status": 1, "note_id": 1, "progress": 1, "extract_duration": 1})
    if not u:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "status": u.get("status"),
        "note_id": str(u.get("note_id")),
        "progress": u.get("progress", {}),
        "extract_duration": u.get("extract_duration", 0)
    })
