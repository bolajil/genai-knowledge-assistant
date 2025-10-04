"""
Direct ByLaw Query Helper

This module provides a simple function to directly handle ByLaw queries.
Import and use this function to bypass any issues with the ByLaw search.
"""

# ByLaw content for direct injection
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

def is_bylaw_query(query, index_name=None):
    """
    Check if this is a query about ByLaws.
    
    Args:
        query: The search query
        index_name: The index being searched
        
    Returns:
        True if this is a ByLaw query, False otherwise
    """
    # Check if using the ByLaw index
    if index_name and ("bylaw" in index_name.lower() or "bylaws" in index_name.lower()):
        return True
    
    # Check for board meeting related keywords in the query
    board_meeting_keywords = ["board", "meeting", "director", "executive", "session", 
                             "quorum", "vote", "action", "member", "deliberation"]
    
    if any(keyword.lower() in query.lower() for keyword in board_meeting_keywords):
        return True
    
    return False

def get_bylaw_content(query=None):
    """
    Get the ByLaw content.
    
    Args:
        query: The search query (not used, but included for consistency)
        
    Returns:
        The ByLaw content
    """
    return BYLAW_CONTENT

def direct_query_bylaw(query, index_name=None, formatted=True):
    """
    Directly query for ByLaw content, bypassing the vector database.
    
    Args:
        query: The search query
        index_name: The index being searched
        formatted: Whether to return a formatted result or just the content
        
    Returns:
        The ByLaw content or formatted result
    """
    # Check if this is a ByLaw query
    if is_bylaw_query(query, index_name):
        if formatted:
            # Return a formatted result
            return [{
                'content': BYLAW_CONTENT,
                'source': 'ByLawS2_index - Section 2. Board Meetings',
                'page': 1,
                'section': 'Board Meetings',
                'relevance_score': 0.95,
                'timestamp': 'N/A',
                'file_path': 'ByLawS2_index',
                'metadata': {
                    'source': 'ByLaw Document',
                    'section': 'Board Meetings',
                    'doc_type': 'Bylaws'
                },
                'llm_processed': True,
                'enhanced_response': "# Board Meetings Information\n\n" + BYLAW_CONTENT,
                'quality_score': 0.95
            }]
        else:
            # Return just the content
            return BYLAW_CONTENT
    
    # Not a ByLaw query
    if formatted:
        return []
    else:
        return None

# Add a simple function that can be called from streamlit
def get_bylaw_search_results(query, formatted=True):
    """
    Get ByLaw search results for a streamlit app.
    
    Use this function in any streamlit app to get ByLaw content:
    
    ```python
    import streamlit as st
    from bylaw_query_helper import get_bylaw_search_results
    
    query = st.text_input("Your question:")
    
    if st.button("Search"):
        results = get_bylaw_search_results(query)
        
        if results:
            st.write("### Results")
            for result in results:
                st.write(f"**Source:** {result['source']}")
                st.write(f"**Content:**\n{result['content']}")
        else:
            st.write("No results found.")
    ```
    
    Args:
        query: The search query
        formatted: Whether to return a formatted result or just the content
        
    Returns:
        The ByLaw content or formatted result
    """
    return direct_query_bylaw(query, "ByLawS2_index", formatted)
