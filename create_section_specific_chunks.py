"""
Create section-specific chunks for better query matching
"""
import re
from pathlib import Path

def create_section_chunks():
    """Create individual chunks for each section to improve search accuracy"""
    
    extracted_text_path = Path("data/indexes/ByLawS2_index/extracted_text.txt")
    
    with open(extracted_text_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find Section 6 specifically (Removal of Directors and Vacancies)
    section_6_pattern = r'(Section 6\. Removal of Directors and Vacancies.*?)(?=Section \d+\.|B\. Meetings|$)'
    section_6_match = re.search(section_6_pattern, content, re.DOTALL | re.IGNORECASE)
    
    if section_6_match:
        section_6_content = section_6_match.group(1).strip()
        print("Found Section 6 - Removal of Directors and Vacancies:")
        print("=" * 60)
        print(section_6_content)
        print("=" * 60)
        
        # Create a dedicated file for Section 6
        section_6_path = Path("data/indexes/ByLawS2_index/section_6_removal_vacancies.txt")
        with open(section_6_path, 'w', encoding='utf-8') as f:
            f.write(section_6_content)
        
        print(f"Created dedicated file: {section_6_path}")
    else:
        print("Section 6 not found with regex pattern")
        
        # Try alternative search
        removal_start = content.find("Removal of Directors and Vacancies")
        if removal_start != -1:
            # Find the end of this section
            next_section_start = content.find("B. Meetings", removal_start)
            if next_section_start == -1:
                next_section_start = content.find("Section 1. Organizational", removal_start)
            
            if next_section_start != -1:
                section_content = content[removal_start:next_section_start].strip()
                print("Found Section 6 content by text search:")
                print("=" * 60)
                print(section_content)
                print("=" * 60)
                
                # Create a dedicated file for Section 6
                section_6_path = Path("data/indexes/ByLawS2_index/section_6_removal_vacancies.txt")
                with open(section_6_path, 'w', encoding='utf-8') as f:
                    f.write(section_content)
                
                print(f"Created dedicated file: {section_6_path}")
            else:
                print("Could not find end of Section 6")
        else:
            print("'Removal of Directors and Vacancies' text not found")
    
    # Also create other important sections
    sections_to_extract = [
        ("Section 2. Board Meetings", "section_2_board_meetings.txt"),
        ("Section 3. Notice of Meetings", "section_3_notice_meetings.txt"),
        ("Section 4. Special Meetings", "section_4_special_meetings.txt"),
        ("Section 5. Nomination of Directors", "section_5_nomination_directors.txt")
    ]
    
    for section_name, filename in sections_to_extract:
        section_start = content.find(section_name)
        if section_start != -1:
            # Find next section or end
            next_section = content.find("Section ", section_start + len(section_name))
            if next_section == -1:
                next_section = content.find("Copyright", section_start)
            
            if next_section != -1:
                section_content = content[section_start:next_section].strip()
                section_path = Path(f"data/indexes/ByLawS2_index/{filename}")
                with open(section_path, 'w', encoding='utf-8') as f:
                    f.write(section_content)
                print(f"Created: {section_path}")

if __name__ == "__main__":
    create_section_chunks()
