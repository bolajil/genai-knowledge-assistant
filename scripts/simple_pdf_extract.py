import PyPDF2
import os

def extract_bylaws_text():
    """Simple extraction to see what we're working with"""
    pdf_path = r"c:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\data\uploads\Bylaws.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found at: {pdf_path}")
        return
    
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            print(f"📄 PDF has {len(reader.pages)} pages")
            
            # Extract first few pages to see structure
            sample_text = ""
            for page_num in range(min(3, len(reader.pages))):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                sample_text += f"\n--- PAGE {page_num + 1} ---\n"
                sample_text += page_text
            
            print(f"📊 Extracted {len(sample_text):,} characters from first 3 pages")
            
            # Save sample
            with open("bylaws_sample.txt", "w", encoding="utf-8") as f:
                f.write(sample_text)
            
            # Show first part of text
            print("\n📝 SAMPLE TEXT (first 1000 characters):")
            print("="*60)
            print(sample_text[:1000])
            print("="*60)
            
            # Search for board-related terms
            board_terms = ["board", "director", "power", "authority", "responsibility"]
            found_terms = []
            
            for term in board_terms:
                if term.lower() in sample_text.lower():
                    found_terms.append(term)
            
            print(f"\n🔍 Found these board-related terms: {found_terms}")
            
            # Look for specific phrases
            key_phrases = [
                "powers of the board",
                "board shall have",
                "duties of directors",
                "board of directors"
            ]
            
            print(f"\n🎯 Searching for key phrases:")
            for phrase in key_phrases:
                if phrase.lower() in sample_text.lower():
                    print(f"✓ Found: '{phrase}'")
                    # Show context
                    lines = sample_text.split('\n')
                    for i, line in enumerate(lines):
                        if phrase.lower() in line.lower():
                            start = max(0, i-2)
                            end = min(len(lines), i+3)
                            context = '\n'.join(lines[start:end])
                            print(f"Context:\n{context}\n")
                            break
                else:
                    print(f"❌ Not found: '{phrase}'")
            
            return sample_text
            
    except Exception as e:
        print(f"❌ Error extracting PDF: {e}")
        return None

if __name__ == "__main__":
    extract_bylaws_text()
