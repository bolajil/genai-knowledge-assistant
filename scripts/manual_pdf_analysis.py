"""
Manual PDF Analysis - Extract and analyze Bylaws.pdf content
This script will work with basic Python and show extraction samples
"""

import os
import re

def analyze_pdf_file():
    """Analyze the PDF file and extract readable content"""
    pdf_path = r"c:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\data\uploads\Bylaws.pdf"
    
    print("🔍 NUCLEAR PDF EXTRACTION ANALYSIS")
    print("="*60)
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found at: {pdf_path}")
        return None
    
    # Get file info
    size = os.path.getsize(pdf_path)
    print(f"✓ Found Bylaws.pdf ({size:,} bytes, {size/1024/1024:.1f} MB)")
    
    try:
        # Read PDF as binary and look for text patterns
        with open(pdf_path, 'rb') as f:
            content = f.read()
        
        print(f"📄 Read {len(content):,} bytes from PDF")
        
        # Convert to string for analysis (ignore encoding errors)
        content_str = content.decode('latin-1', errors='ignore')
        
        # Look for PDF structure
        if content_str.startswith('%PDF'):
            version_match = re.search(r'%PDF-(\d\.\d)', content_str)
            if version_match:
                print(f"✓ Valid PDF file (version {version_match.group(1)})")
        
        # Extract readable text segments
        print(f"\n🔍 EXTRACTING READABLE TEXT...")
        
        # Find text that looks like readable content
        text_patterns = [
            r'[A-Z][A-Za-z\s,\.;:!?\-\(\)]{30,}',  # Sentences starting with capital
            r'ARTICLE\s+[IVX]+[A-Za-z\s,\.;:!?\-\(\)]{20,}',  # Articles
            r'SECTION\s+\d+[A-Za-z\s,\.;:!?\-\(\)]{20,}',  # Sections
            r'Board\s+of\s+Directors[A-Za-z\s,\.;:!?\-\(\)]{20,}',  # Board content
        ]
        
        all_matches = []
        for pattern in text_patterns:
            matches = re.findall(pattern, content_str, re.IGNORECASE)
            all_matches.extend(matches)
        
        # Remove duplicates and clean up
        unique_matches = list(set(all_matches))
        cleaned_matches = [match.strip() for match in unique_matches if len(match.strip()) > 30]
        
        print(f"📝 Found {len(cleaned_matches)} readable text segments")
        
        if cleaned_matches:
            # Show samples
            print(f"\n📄 TEXT SAMPLES:")
            print("-"*60)
            
            board_related = []
            other_content = []
            
            for i, match in enumerate(cleaned_matches[:15]):  # Show first 15
                clean_text = re.sub(r'\s+', ' ', match).strip()
                
                if any(term in clean_text.lower() for term in ['board', 'director', 'power', 'authority']):
                    board_related.append(clean_text)
                    print(f"🎯 BOARD-RELATED #{len(board_related)}:")
                    print(f"   {clean_text[:200]}...")
                else:
                    other_content.append(clean_text)
                    if len(other_content) <= 3:  # Show first 3 other content
                        print(f"📋 GENERAL #{len(other_content)}:")
                        print(f"   {clean_text[:200]}...")
                
                print()
            
            # Search for specific board powers content
            print(f"\n🎯 SEARCHING FOR BOARD POWERS CONTENT:")
            print("-"*60)
            
            key_phrases = [
                "powers of the board",
                "board shall have power",
                "duties of directors",
                "responsibilities of the board",
                "authority of the board",
                "board of directors shall"
            ]
            
            found_phrases = []
            for phrase in key_phrases:
                for match in cleaned_matches:
                    if phrase.lower() in match.lower():
                        found_phrases.append((phrase, match))
                        print(f"✓ FOUND: '{phrase}'")
                        print(f"   Context: {match[:300]}...")
                        print()
                        break
                else:
                    print(f"❌ NOT FOUND: '{phrase}'")
            
            # Save extracted content
            output_content = f"""BYLAWS PDF EXTRACTION ANALYSIS
{'='*60}

FILE INFO:
- Path: {pdf_path}
- Size: {size:,} bytes ({size/1024/1024:.1f} MB)
- Readable segments found: {len(cleaned_matches)}

BOARD-RELATED CONTENT:
{'='*40}
"""
            
            for i, content in enumerate(board_related):
                output_content += f"\nBOARD CONTENT #{i+1}:\n{content}\n{'-'*40}\n"
            
            output_content += f"\nOTHER CONTENT SAMPLES:\n{'='*40}\n"
            for i, content in enumerate(other_content[:5]):
                output_content += f"\nGENERAL CONTENT #{i+1}:\n{content}\n{'-'*40}\n"
            
            output_content += f"\nFOUND PHRASES:\n{'='*40}\n"
            for phrase, context in found_phrases:
                output_content += f"\nPHRASE: {phrase}\nCONTEXT: {context}\n{'-'*40}\n"
            
            # Save to file
            with open("bylaws_extraction_analysis.txt", "w", encoding="utf-8") as f:
                f.write(output_content)
            
            print(f"💾 Full analysis saved to: bylaws_extraction_analysis.txt")
            
            # Assessment
            print(f"\n📊 EXTRACTION ASSESSMENT:")
            print(f"   • Board-related segments: {len(board_related)}")
            print(f"   • Key phrases found: {len(found_phrases)}")
            print(f"   • Total readable content: {len(cleaned_matches)}")
            
            if len(board_related) > 0:
                print(f"✅ SUCCESS: Found board-related content!")
                print(f"   Ready to create semantic index")
            else:
                print(f"⚠️  LIMITED: Little board content found")
                print(f"   May need OCR or different extraction method")
            
            return cleaned_matches
            
        else:
            print(f"❌ No readable text found")
            print(f"   PDF might be:")
            print(f"   • Scanned images (needs OCR)")
            print(f"   • Encrypted or password protected")
            print(f"   • Using complex encoding")
            return None
            
    except Exception as e:
        print(f"❌ Error analyzing PDF: {e}")
        return None

if __name__ == "__main__":
    analyze_pdf_file()
