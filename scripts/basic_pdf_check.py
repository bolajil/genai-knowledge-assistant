import os
import sys

def check_pdf_exists():
    """Check if the PDF exists and get basic info"""
    pdf_path = r"c:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\data\uploads\Bylaws.pdf"
    
    if os.path.exists(pdf_path):
        size = os.path.getsize(pdf_path)
        print(f"✓ Found Bylaws.pdf")
        print(f"📊 File size: {size:,} bytes ({size/1024/1024:.1f} MB)")
        print(f"📁 Path: {pdf_path}")
        
        # Try to read first few bytes to check if it's a valid PDF
        try:
            with open(pdf_path, 'rb') as f:
                header = f.read(10)
                if header.startswith(b'%PDF'):
                    print(f"✓ Valid PDF file (version detected)")
                else:
                    print(f"❌ File doesn't appear to be a valid PDF")
        except Exception as e:
            print(f"❌ Error reading file: {e}")
        
        return pdf_path
    else:
        print(f"❌ PDF not found at: {pdf_path}")
        return None

def try_simple_extraction():
    """Try basic text extraction without external libraries"""
    pdf_path = check_pdf_exists()
    if not pdf_path:
        return
    
    print(f"\n🔍 Attempting basic text extraction...")
    
    # Try to find readable text in the PDF
    try:
        with open(pdf_path, 'rb') as f:
            content = f.read()
            
            # Look for text streams in PDF
            text_content = ""
            content_str = content.decode('latin-1', errors='ignore')
            
            # Simple approach: look for readable text between stream markers
            import re
            
            # Find text that might be readable
            readable_parts = re.findall(r'[A-Za-z][A-Za-z\s,\.;:!?\-]{20,}', content_str)
            
            print(f"📝 Found {len(readable_parts)} potential text segments")
            
            if readable_parts:
                print(f"\n📄 SAMPLE TEXT SEGMENTS:")
                print("="*60)
                for i, segment in enumerate(readable_parts[:5]):  # Show first 5
                    print(f"{i+1}. {segment[:100]}...")
                print("="*60)
                
                # Look for board-related content
                board_keywords = ["board", "director", "power", "authority", "bylaw"]
                found_keywords = []
                
                for segment in readable_parts:
                    for keyword in board_keywords:
                        if keyword.lower() in segment.lower():
                            found_keywords.append(keyword)
                
                print(f"\n🎯 Found board-related keywords: {set(found_keywords)}")
                
                # Save sample
                sample_text = "\n\n".join(readable_parts[:10])
                with open("bylaws_basic_sample.txt", "w", encoding="utf-8") as f:
                    f.write(sample_text)
                print(f"💾 Sample saved to: bylaws_basic_sample.txt")
                
            else:
                print(f"❌ No readable text found - PDF might be:")
                print(f"   • Scanned images (needs OCR)")
                print(f"   • Encrypted or protected")
                print(f"   • Using complex encoding")
                
    except Exception as e:
        print(f"❌ Error during extraction: {e}")

if __name__ == "__main__":
    try_simple_extraction()
