from flask import Blueprint, jsonify, send_file, request
from models.mongo_models import notes
from core.utils import export_to_pdf, export_to_docx
from bson import ObjectId
from jose import jwt
from config import Config
import os

bp = Blueprint('notes', __name__, url_prefix='/api')


def get_user_from_auth():
    """Extract user_id from JWT, fallback to demo_user if not logged in."""
    auth = request.headers.get("Authorization", "")
    if not auth:
        return "demo_user"
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        try:
            payload = jwt.decode(parts[1], Config.JWT_SECRET, algorithms=["HS256"])
            return str(payload.get("sub", "demo_user"))
        except Exception:
            return "demo_user"
    return "demo_user"


def get_note_by_id(note_id: str):
    """Try fetching note by string _id or ObjectId."""
    n = notes.find_one({"_id": note_id})
    if not n:
        try:
            n = notes.find_one({"_id": ObjectId(note_id)})
        except:
            n = None
    return n


@bp.route('/notes/<note_id>', methods=['GET'])
def get_note(note_id):
    n = get_note_by_id(note_id)
    if not n:
        return jsonify({"error": "Note not found"}), 404

    return jsonify({
        "note_id": str(n["_id"]),
        "final_notes": n.get("final_notes", ""),
        "raw_transcript": n.get("raw_transcript", ""),
        "cleaned_transcript": n.get("cleaned_transcript", ""),
        "created_at": n["created_at"].isoformat() if n.get("created_at") else None
    })


@bp.route('/history', methods=['GET'])
def history():
    user_id = get_user_from_auth()

    # Guest users ke liye history block
    if user_id == "demo_user":
        return jsonify({"error": "Login required to view history"}), 401

    docs = list(notes.find({"user_id": user_id}).sort("created_at", -1).limit(50))
    out = [
        {
            "note_id": str(d["_id"]),
            "created_at": d["created_at"].isoformat() if d.get("created_at") else None,
            "summary_preview": (d.get("final_notes", "")[:120] + "...") if d.get("final_notes") else ""
        }
        for d in docs
    ]
    return jsonify(out)


@bp.route('/download/pdf/<note_id>', methods=['GET'])
def download_pdf(note_id):
    n = get_note_by_id(note_id)
    if not n:
        return jsonify({"error": "Note not found in DB"}), 404

    os.makedirs("storage/exports", exist_ok=True)
    path = f"storage/exports/{note_id}.pdf"
    export_to_pdf(n.get("final_notes", ""), path)
    return send_file(path, as_attachment=True,mimetype="application/pdf")


@bp.route('/download/docx/<note_id>', methods=['GET'])
def download_docx(note_id):
    n = get_note_by_id(note_id)
    if not n:
        return jsonify({"error": "Note not found in DB"}), 404

    os.makedirs("storage/exports", exist_ok=True)
    path = f"storage/exports/{note_id}.docx"
    export_to_docx(n.get("final_notes", ""), path)
    return send_file(path, as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
