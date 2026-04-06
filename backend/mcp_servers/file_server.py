import os

import PyPDF2
import ollama

try:
    from docx import Document
except Exception:
    Document = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from PIL import Image
except Exception:
    Image = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploaded_files")
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx", ".png", ".jpg", ".jpeg", ".bmp"}


def ensure_upload_dir():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def save_uploaded_file(filename, file_bytes):
    ensure_upload_dir()
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    with open(file_path, "wb") as file:
        file.write(file_bytes)
    return file_path


def get_latest_uploaded_document():
    ensure_upload_dir()
    files = [
        os.path.join(UPLOAD_FOLDER, name)
        for name in os.listdir(UPLOAD_FOLDER)
        if os.path.splitext(name)[1].lower() in SUPPORTED_EXTENSIONS
    ]

    if not files:
        return None

    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def extract_pdf_text(file_path):
    text = ""
    with open(file_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    return text.strip()


def extract_text_file(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read().strip()


def extract_docx_text(file_path):
    if not Document:
        return "DOCX support is unavailable. Install python-docx to summarize Word files."

    document = Document(file_path)
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(paragraphs)


def extract_image_text(file_path):
    if not pytesseract or not Image:
        return "Image OCR support is unavailable. Install pytesseract and pillow to summarize images."

    image = Image.open(file_path)
    return pytesseract.image_to_string(image).strip()


def extract_document_text(file_path):
    extension = os.path.splitext(file_path)[1].lower()

    try:
        if extension == ".pdf":
            return extract_pdf_text(file_path)
        if extension == ".txt":
            return extract_text_file(file_path)
        if extension == ".docx":
            return extract_docx_text(file_path)
        if extension in {".png", ".jpg", ".jpeg", ".bmp"}:
            return extract_image_text(file_path)
    except Exception as error:
        return f"Error reading document: {error}"

    return f"Unsupported file type: {extension}"


def summarize_document(file_path):
    text = extract_document_text(file_path)

    if not text:
        return "Could not extract readable text from that file."

    if text.startswith("DOCX support is unavailable") or text.startswith("Image OCR support is unavailable"):
        return text

    prompt = f"""
Summarize the following document in clear bullet points with a short title and key takeaways.

Document:
{text[:6000]}
"""

    response = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]
