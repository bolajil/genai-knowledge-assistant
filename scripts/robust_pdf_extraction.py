import pdfplumber

def extract_text_from_pdf(pdf_path):
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    return full_text

# Usage
pdf_path = "path/to/your/Bylaw02.pdf"
text = extract_text_from_pdf(pdf_path)
with open("extracted_text.txt", "w", encoding="utf-8") as f:
    f.write(text)
