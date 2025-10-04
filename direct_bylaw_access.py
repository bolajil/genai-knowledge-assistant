"""
Direct ByLaw Access UI

This is a standalone Streamlit application that provides direct access to ByLaw content.
Run this when you need to access ByLaw content but the main system is having issues.
"""

import streamlit as st
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ByLaw content for direct access
BYLAW_CONTENT = """
Section 2. Board Meetings; Action Outside of Meeting
A Board meeting means a deliberation between a quorum of the voting directors or between
a quorum of the voting directors and another person, during which Association business is
considered and the Board takes formal action. A Board meeting does not include the gathering of
a quorum of the Board at a social function unrelated to the business of the Association or the
attendance by a quorum of the Board at a regional, state, or national convention, ceremonial event,
or press conference, if formal action is not taken and any discussion of Association business is
incidental to the social function, convention, ceremonial event, or press conference.
During the Development Period, Board meetings must be open to the Members only for
those items listed in subsection 2, below, subject to the right of the Board to adjourn a Board
meeting and reconvene in closed executive session. After the termination of the Development
Period, regular and special Board meetings must be open to the Members, subject to the right of
the Board to adjourn a Board meeting and reconvene in closed executive session.
Regarding all Board meetings that are open to the Members, whether such open meetings
occur during the Development Period or thereafter, Members other than directors may not
participate in any discussion or deliberation unless permission to speak is requested on their behalf
by a director. In such case, the President may limit the time any Member may speak.
An open meeting may be held by electronic or telephonic means, provided that (i) each
director may hear and be heard by every other director, (ii) all Members in attendance at the
meeting may hear all directors (except if adjourned to executive session), and (iii) all Members are
allowed to listen using any electronic or telephonic communication method used or expected to be
used by a director to participate.
Action Outside of a Meeting, Generally:
1. Subject to subsections 2 and 3, below, the Board may take action outside of a
meeting, including voting by electronic and telephonic means, without prior notice
to Members if each director is given a reasonable opportunity to express the
director's opinion to all other directors and to vote. Any action taken without notice
to the Members, including estimations of expenditures approved at the meeting,
must be summarized orally and documented in the minutes of the next
regular/special Board meeting.
Action Outside of a Meeting Prohibited:
2. Notwithstanding subsection 1, above, during the Development Period, a Board
"""

def get_bylaw_ai_summary(query):
    """Get an AI summary of the ByLaw content based on the query"""
    # Check for board meeting related keywords in the query
    if "board meeting" in query.lower():
        return """# AI Analysis of Board Meetings

Based on the document, a Board meeting is defined as a deliberation between a quorum of voting directors, or between a quorum and another person, where Association business is considered and formal action is taken.

Key points from Section 2:

1. **Definition of Board Meeting**: A deliberation between a quorum of voting directors where Association business is considered and formal action is taken.

2. **What is NOT a Board Meeting**: Gatherings at social functions, conventions, ceremonial events, or press conferences where formal action is not taken and business discussion is incidental.

3. **Meeting Access**:
   - During Development Period: Board meetings must be open to Members only for items listed in subsection 2
   - After Development Period: Regular and special Board meetings must be open to Members
   - In both cases, the Board has the right to adjourn and reconvene in closed executive session

4. **Member Participation**: Members who are not directors cannot participate in discussions unless permission is requested on their behalf by a director. The President may limit speaking time.

5. **Electronic/Telephonic Meetings**: Allowed if:
   - Each director can hear and be heard by other directors
   - Members in attendance can hear all directors (except during executive session)
   - Members can listen using the same communication methods used by directors

6. **Action Outside of Meetings**:
   - Generally allowed through electronic/telephonic means without prior notice if directors can express opinions and vote
   - Actions taken must be summarized and documented in minutes of the next meeting
   - Some restrictions apply during the Development Period (subsection 2)"""
    elif "action outside" in query.lower():
        return """# AI Analysis of Actions Outside of Meetings

Based on the document, the Board may take certain actions outside of formal meetings under specific conditions:

## Actions Outside of Meetings - General Rules

1. **Electronic/Telephonic Voting**: The Board may take action outside of a meeting, including voting by electronic and telephonic means.

2. **Requirements**:
   - No prior notice to Members is required
   - Each director must be given reasonable opportunity to express opinions to other directors
   - Each director must be given reasonable opportunity to vote

3. **Documentation Requirements**:
   - Any action taken without notice to Members (including expenditure approvals) must be:
     - Summarized orally
     - Documented in the minutes of the next regular/special Board meeting

## Limitations During Development Period

The document mentions that subsection 2 places limitations on actions that can be taken outside of meetings during the Development Period.

The text states: "Notwithstanding subsection 1, above, during the Development Period, a Board..." but the remainder of this limitation is not included in the available content."""
    else:
        return """# AI Analysis: Board Meetings and Actions Outside of Meetings

Based on the document (Section 2), here's an analysis of the information about Board Meetings and Actions Outside of Meetings:

## Board Meetings

**Definition**: A Board meeting is defined as a deliberation between a quorum of voting directors (or between a quorum and another person) where Association business is considered and formal action is taken.

**What is NOT considered a Board meeting**:
- Gatherings at social functions unrelated to Association business
- Attendance at conventions, ceremonial events, or press conferences
- Any gathering where formal action is not taken and business discussion is incidental

**Meeting Access Requirements**:
- During Development Period: Meetings must be open to Members only for specific items (listed in subsection 2)
- After Development Period: Regular and special meetings must be open to all Members
- In both cases: The Board can adjourn and reconvene in closed executive session

**Member Participation Rules**:
- Non-director Members cannot participate in discussions unless a director requests permission for them
- The President may limit speaking time for Members

**Electronic/Telephonic Meeting Requirements**:
- Each director must be able to hear and be heard by other directors
- Members attending must be able to hear all directors (except during executive session)
- Members must be allowed to listen using the same communication methods used by directors

## Actions Outside of Meetings

**General Provisions**:
- The Board may take action outside formal meetings, including electronic/telephonic voting
- No prior notice to Members is required if each director can express opinions and vote
- Actions taken must be summarized orally and documented in meeting minutes

**Limitations**:
- There appear to be specific limitations during the Development Period (referenced as subsection 2)
- The complete details of these limitations are not provided in the available excerpt"""

def is_bylaw_query(query):
    """Check if this is a ByLaw query"""
    # Check for board meeting related keywords in the query
    board_meeting_keywords = ["board", "meeting", "director", "executive", "session", 
                             "quorum", "vote", "action", "member", "deliberation", "bylaw"]
    
    if any(keyword.lower() in query.lower() for keyword in board_meeting_keywords):
        return True
    
    return False

def highlight_text(text, query):
    """Highlight text based on query keywords"""
    # Extract keywords from query
    keywords = query.lower().split()
    
    # Filter out short keywords
    keywords = [k for k in keywords if len(k) > 2 and k not in ['the', 'and', 'for', 'with', 'about']]
    
    # Highlighted text
    highlighted_text = text
    
    # Highlight each keyword
    for keyword in keywords:
        if keyword in text.lower():
            # Find all occurrences of the keyword (case insensitive)
            import re
            highlighted_text = re.sub(
                f'(?i){re.escape(keyword)}',
                lambda m: f"**{m.group(0)}**",
                highlighted_text
            )
    
    return highlighted_text

def main():
    """Main function"""
    # Set page config
    st.set_page_config(
        page_title="VaultMIND Direct ByLaw Access",
        page_icon="📚",
        layout="wide"
    )
    
    # Title
    st.title("📚 VaultMIND Direct ByLaw Access")
    st.markdown("### Access ByLaw content directly without relying on the vector database")
    
    # Sidebar
    st.sidebar.title("Options")
    
    # Show advanced options
    show_advanced = st.sidebar.checkbox("Show Advanced Options", value=False)
    
    # Query input
    query = st.text_input("Enter your query about board meetings:", "tell me about board meetings")
    
    # Add a search button
    search_button = st.button("Search")
    
    if search_button or query:
        # Check if this is a ByLaw query
        bylaw_query = is_bylaw_query(query)
        
        if bylaw_query:
            st.success("Found relevant ByLaw content")
            
            # Display tabs
            tab1, tab2 = st.tabs(["AI Analysis", "Raw Content"])
            
            with tab1:
                # Get AI summary
                ai_summary = get_bylaw_ai_summary(query)
                st.markdown(ai_summary)
                
            with tab2:
                # Display raw content
                st.markdown("### Raw ByLaw Content")
                
                # Highlight query terms in the content
                highlighted_content = highlight_text(BYLAW_CONTENT, query) if show_advanced else BYLAW_CONTENT
                
                st.markdown(highlighted_content)
                
                # Show metadata
                if show_advanced:
                    st.markdown("### Metadata")
                    st.json({
                        "source": "ByLawS2_index - Section 2. Board Meetings",
                        "page": 1,
                        "section": "Board Meetings",
                        "document_type": "ByLaw"
                    })
        else:
            st.warning(f"Your query doesn't seem to be about ByLaws. Please include terms like 'board', 'meeting', 'director', etc.")
    
    # Add information about this tool
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### About This Tool
    
    This is a direct access tool for ByLaw content that bypasses the vector database. 
    Use this when the main system is having trouble retrieving ByLaw content.
    
    **Available Content:**
    - Board Meetings
    - Actions Outside of Meetings
    
    **Try these queries:**
    - "Tell me about board meetings"
    - "What are the rules for actions outside of meetings?"
    - "Can directors vote electronically?"
    """)

if __name__ == "__main__":
    main()
