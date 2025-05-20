import os
import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import tempfile
import cv2
import numpy as np
from PyPDF2 import PdfReader
from pdfminer.high_level import extract_text as pdfminer_extract

def clean_text(text):
    """
    Cleans raw text extracted from files:
    - Removes hyphenated line breaks
    - Converts single newlines to spaces inside paragraphs
    - Preserves paragraph spacing
    - Collapses extra spaces
    """
    text = re.sub(r'-\n', '', text)
    text = re.sub(r'\n{2,}', '\n\n', text)
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def extract_text_from_files(uploaded_files):
    """
    Accepts a list of uploaded files and extracts clean text.
    Supports PDF, TXT, and image (PNG, JPG, JPEG) formats.
    Returns:
    - Full concatenated cleaned text
    - List of filenames (used for logging)
    """
    full_text = ""
    filenames = []
    ocr_config = '--psm 3 --oem 3'

    for uploaded_file in uploaded_files:
        suffix = os.path.splitext(uploaded_file.name)[-1].lower()
        filenames.append(uploaded_file.name)
        
        # --- PDF Handling with fallback ---
        if suffix == ".pdf":
            try:
                # Try extracting with PDFMiner first
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name
                pdfminer_text = pdfminer_extract(tmp_path)
                if pdfminer_text.strip():
                    full_text += f"\n\n--- {uploaded_file.name} (PDFMiner) ---\n\n" + clean_text(pdfminer_text) + "\n"
                    os.remove(tmp_path)
                    continue
            except:
                pass
            
            try:
                # Fallback to PyPDF2 with OCR page-by-page
                reader = PdfReader(tmp_path)
                extracted = False
                for i, page in enumerate(reader.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        full_text += f"\n\n--- {uploaded_file.name} Page {i} (PyPDF2) ---\n\n" + clean_text(text) + "\n"
                        extracted = True
                    else:
                        # Fallback OCR via OpenCV for noisy pages
                        try:
                            from pdf2image import convert_from_path
                            images = convert_from_path(tmp_path, first_page=i, last_page=i, dpi=300)
                            image = np.array(images[0])
                            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                            blurred = cv2.medianBlur(gray, 3)
                            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                           cv2.THRESH_BINARY, 11, 2)
                            resized = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                            kernel = np.ones((1, 1), np.uint8)
                            processed = cv2.dilate(resized, kernel, iterations=1)
                            processed = cv2.erode(processed, kernel, iterations=1)
                            ocr_text = pytesseract.image_to_string(processed, config=ocr_config)
                            full_text += f"\n\n--- {uploaded_file.name} OCR Page {i} ---\n\n" + clean_text(ocr_text) + "\n"
                            extracted = True
                        except Exception as ocr_error:
                            full_text += f"[OCR failed on page {i}: {ocr_error}]\n"
                os.remove(tmp_path)
                if not extracted:
                    full_text += f"[No usable text found in {uploaded_file.name}]\n"
            except Exception as e:
                full_text += f"[ERROR reading {uploaded_file.name}: {e}]\n"

        # --- TXT Handling ---
        elif suffix == ".txt":
            try:
                text = uploaded_file.read().decode("utf-8")

                # Detect and clean subtitle-style transcripts
                timestamp_lines = len(re.findall(r'^\d{1,2}:\d{2}\s*$', text, flags=re.MULTILINE))
                total_lines = len(text.splitlines())
                is_transcript = timestamp_lines > 0 and (timestamp_lines / total_lines) > 0.2
                if is_transcript:
                    text = re.sub(r'\d{2}:\d{2}:\d{2}\s*-->\s*\d{2}:\d{2}:\d{2}', '', text)
                    text = re.sub(r'^\d{1,2}:\d{2}\s*$', '', text, flags=re.MULTILINE)

                full_text += f"\n\n--- {uploaded_file.name} ---\n\n" + clean_text(text) + "\n"
            except Exception as e:
                full_text += f"[ERROR reading {uploaded_file.name}: {e}]\n"

        # --- Image OCR Handling ---
        elif suffix in [".png", ".jpg", ".jpeg"]:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name
                image = cv2.imread(tmp_path)
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                blurred = cv2.medianBlur(gray, 3)
                thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                               cv2.THRESH_BINARY, 11, 2)
                resized = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                kernel = np.ones((1, 1), np.uint8)
                processed = cv2.dilate(resized, kernel, iterations=1)
                processed = cv2.erode(processed, kernel, iterations=1)
                ocr_text = pytesseract.image_to_string(processed, config=ocr_config)
                full_text += f"\n\n--- {uploaded_file.name} ---\n\n" + clean_text(ocr_text) + "\n"
                os.remove(tmp_path)
            except Exception as e:
                full_text += f"[ERROR reading image {uploaded_file.name}: {e}]\n"

    return full_text.strip(), filenames