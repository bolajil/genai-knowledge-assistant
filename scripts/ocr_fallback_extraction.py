from pdf2image import convert_from_path
import pytesseract

def extract_text_with_ocr(pdf_path):
    images = convert_from_path(pdf_path)
    full_text = ""
    for image in images:
        text = pytesseract.image_to_string(image)
        full_text += text + "\n"
    return full_text

# Usage (ensure Tesseract is installed)
pdf_path = "path/to/your/Bylaw02.pdf"
text = extract_text_with_ocr(pdf_path)
with open("extracted_text_ocr.txt", "w", encoding="utf-8") as f:
    f.write(text)
