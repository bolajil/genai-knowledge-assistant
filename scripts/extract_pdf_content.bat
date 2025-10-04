@echo off
echo Nuclear PDF Extraction Analysis
echo ================================

cd /d "c:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant"

echo Checking for PDF file...
if exist "data\uploads\Bylaws.pdf" (
    echo ✓ Found Bylaws.pdf
    dir "data\uploads\Bylaws.pdf"
) else (
    echo ❌ Bylaws.pdf not found
    exit /b 1
)

echo.
echo Attempting Python extraction...
python -c "
import os
pdf_path = r'data\uploads\Bylaws.pdf'
if os.path.exists(pdf_path):
    size = os.path.getsize(pdf_path)
    print(f'PDF Size: {size:,} bytes ({size/1024/1024:.1f} MB)')
    
    # Try basic text extraction
    with open(pdf_path, 'rb') as f:
        content = f.read()
        print(f'Read {len(content):,} bytes')
        
        # Look for readable text
        content_str = content.decode('latin-1', errors='ignore')
        
        # Find potential text content
        import re
        text_segments = re.findall(r'[A-Za-z][A-Za-z\s,\.;:!?\-]{30,}', content_str)
        
        print(f'Found {len(text_segments)} text segments')
        
        # Look for board-related content
        board_content = []
        for segment in text_segments:
            if any(term in segment.lower() for term in ['board', 'director', 'power', 'authority']):
                board_content.append(segment)
        
        print(f'Board-related segments: {len(board_content)}')
        
        # Save sample
        if board_content:
            with open('bylaws_sample_content.txt', 'w', encoding='utf-8') as f:
                f.write('BYLAWS EXTRACTION SAMPLE\n')
                f.write('='*50 + '\n\n')
                for i, content in enumerate(board_content[:5]):
                    f.write(f'SEGMENT {i+1}:\n{content}\n\n')
            print('✓ Sample saved to bylaws_sample_content.txt')
        else:
            print('❌ No board content found')
"

pause
