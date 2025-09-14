import os
import requests
# from fpdf import FPDF
from docx import Document
from moviepy.editor import VideoFileClip
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# --- Font setup for PDF (Unicode safe) ---
FONT_DIR = "storage/fonts"
FONT_PATH = os.path.join(FONT_DIR, "NotoSans.ttf")

def ensure_font():
    """Download NotoSans variable font from Google Fonts repo if not available."""
    os.makedirs(FONT_DIR, exist_ok=True)
    if not os.path.exists(FONT_PATH):
        print("🔽 Downloading NotoSans.ttf ...")
        url = "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans%5Bwdth,wght%5D.ttf"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(FONT_PATH, "wb") as f:
            f.write(r.content)
        print("✅ NotoSans font downloaded!")

# # --- Export Notes to PDF ---
# def export_to_pdf(notes_text, output_path):
#     ensure_font()
#     pdf = FPDF()
#     pdf.add_page()

#     # Register and set Unicode font
#     pdf.add_font("NotoSans", "", FONT_PATH, uni=True)
#     pdf.set_font("NotoSans", size=12)

#     # Accept string or list
#     if isinstance(notes_text, str):
#         lines = notes_text.split("\n")
#     else:
#         lines = list(notes_text)

#     for line in lines:
#         pdf.multi_cell(0, 10, str(line))
#         pdf.multi_cell(0, 10, line.encode("latin-1", "replace").decode("latin-1"))

def export_to_pdf(notes_text, output_path):
    """
    Stable PDF export using reportlab (Unicode + Urdu supported).
    """
    # Font register (Urdu / Arabic ke liye MSung-Light or STSong-Light bhi use ho sakta hai)
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))  # universal Unicode font

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    c.setFont("HeiseiMin-W3", 12)

    # Accept string ya list
    lines = notes_text.split("\n") if isinstance(notes_text, str) else list(notes_text)

    y = height - 50
    for line in lines:
        if y < 50:  # page break
            c.showPage()
            c.setFont("HeiseiMin-W3", 12)
            y = height - 50
        c.drawString(50, y, line)
        y -= 20

    c.save()
    return output_path

    # ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    return output_path

# --- Export Notes to DOCX ---
def export_to_docx(notes_text, output_path):
    doc = Document()
    if isinstance(notes_text, str):
        lines = notes_text.split("\n")
    else:
        lines = list(notes_text)
    for line in lines:
        doc.add_paragraph(str(line))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path

# --- Extract Audio from Video ---
def extract_audio_from_video(video_path, output_path, duration=120):
    """
    Extract first `duration` seconds of audio from a video (e.g. MP4).
    Save as .mp3 file.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    clip = VideoFileClip(video_path)
    audio_clip = None
    try:
        if clip.audio is None:
            raise RuntimeError("No audio track found in video!")

        audio_clip = clip.audio.subclip(0, duration)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        audio_clip.write_audiofile(output_path, codec="mp3")
    finally:
        if audio_clip:
            try:
                audio_clip.close()
            except Exception:
                pass
        if clip:
            try:
                clip.close()
            except Exception:
                pass

    return output_path

# --- Translation helper (uses googletrans, fallback to identity) ---
def translate_text(text, src='auto', target='en'):
    """
    Translate `text` to target language. Uses googletrans if installed.
    Returns translated text or original text on failure.
    """
    try:
        from googletrans import Translator
        translator = Translator()
        # googletrans can fail for long texts at once; be conservative
        # chunk by 5000 chars
        if len(text) <= 4500:
            return translator.translate(text, src=src, dest=target).text
        out = []
        start = 0
        while start < len(text):
            chunk = text[start:start+4500]
            out.append(translator.translate(chunk, src=src, dest=target).text)
            start += 4500
        return "\n".join(out)
    except Exception:
        # translator not available or failed -> return original
        return text

# --- Token/text optimizer (heuristic) ---
def optimize_for_tokens(text, max_tokens=3000):
    """
    Heuristic to reduce text length to approximately max_tokens.
    Approx tokens = chars/4 (simple estimate). Tries to cut at sentence boundary.
    """
    if not text:
        return text
    approx_tokens = len(text) / 4.0
    if approx_tokens <= max_tokens:
        return text

    ratio = max_tokens / approx_tokens
    max_chars = max(200, int(len(text) * ratio))  # ensure some minimum
    cut = text[:max_chars]
    # try to cut at last sentence end
    last_dot = max(cut.rfind('.'), cut.rfind('!\n'), cut.rfind('?\n'))
    if last_dot and last_dot > int(0.5 * max_chars):
        return cut[:last_dot+1]
    # fallback: cut at last newline
    last_nl = cut.rfind('\n')
    if last_nl and last_nl > 0:
        return cut[:last_nl]
    return cut
