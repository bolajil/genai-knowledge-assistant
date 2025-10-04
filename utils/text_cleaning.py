"""
Text Cleaning Utility - With Improved Formatting
Removes PDF artifacts and adds proper paragraph breaks for readability.
"""

import re

def clean_document_text(text: str) -> str:
    """Clean raw text from documents and add proper formatting.

    - Removes page break markers like '--- Page X ---'
    - Removes obvious PDF headers (all-caps lines)
    - Adds paragraph breaks where appropriate
    - Normalizes whitespace
    - Preserves sentence structure and content
    """
    if not text:
        return ""

    # Remove page break markers
    cleaned_text = re.sub(r'\s*--- Page \d+ ---\s*', ' ', text, flags=re.IGNORECASE)

    # Split into lines to process headers
    lines = cleaned_text.split('\n')
    filtered_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip obvious PDF headers (all caps, short, no spaces or minimal spaces)
        if (len(line) > 10 and
            re.match(r'^[A-Z0-9\?\.\-]{15,}$', line) and
            line.count(' ') < 3 and
            not re.search(r'[a-z]', line)):  # No lowercase letters
            continue

        # Skip lines that are just numbers or very short all-caps
        if len(line) < 6 and re.match(r'^[A-Z0-9\s]+$', line):
            continue

        filtered_lines.append(line)

    cleaned_text = '\n'.join(filtered_lines)

    # Add paragraph breaks before sentences that start with uppercase letters
    # This helps break up long text blocks where paragraph breaks were lost
    cleaned_text = re.sub(r'([.!?])\s+([A-Z])', r'\1\n\n\2', cleaned_text)

    # Normalize whitespace (but preserve paragraph breaks)
    cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)  # Multiple spaces to single
    cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)  # Multiple newlines to double

    return cleaned_text.strip()

def test_cleaning():
    """Test the cleaning function"""
    test_text = """structuredpromptwithintheirownapplications,especiallythoseinvolvingAIandnaturallanguageprocessingtaskswherecontext-basedanswersarenecessary. 115
--- Page 116 ---
DOYOUSPEAKGENERATIVEAI?THEPROMPTENGINEERINGBEGINNER’SGUIDE PracticalApplications The"rag-prompt"isinvaluableinapplicationssuchascustomer
lytechnicalinitscommunication.ThisGPTisequippedtohandletaskslikewritingandoptimizingcode,implementingCSS,debugging,andtranslatingfeaturespecificationsintopracticalcodesolutions.Itprovidesprecise,technicalguidanceandcodeexamples,adheringtothelatestindustrystandardsandbestpractices. CodeMavenfocuseson
forstatemanagement,andtipsonminimizingre-renders. PracticalUsage CodeMavenisparticularlyusefulforexperienceddeveloperswhorequireadvanced,technicalassistancewithouttheneedforsimplifiedexplanations.Thissystemisadeptatnavigatingcomplexprojectrequirementsanddeliveringsolutionsthatarebothpracticalandalig
les.ThisGPTavoidsgeneralizationsorsimplisticexplanations,aiminginsteadtoprovidedetailed,technicalinsightssuitableforexperienceddevelopers.Itshouldnotofferadviceoutsidetherealmoffrontenddevelopmentanditsspecifiedtechnologies. 93
--- Page 94 ---
DOYOUSPEAKGENERATIVEAI?THEPROMPTENGINEERINGBEGINNER’SGUIDE
guages,whichenablesthemtoassistdevelopersbyautomatingcodingtasks.ThissectionexploresthepracticaluseofLLMsforgeneratingcodesnippets,whichcanimproveproductivityandaccuracyinsoftwaredevelopment. PromptDesign ExamplePrompt:/Asktheuserfortheirnameandsay"Hello"/ PromptExplanation:Thepromptisstructuredas"""

    print("=== BEFORE ===")
    print(repr(test_text))
    print("\n=== AFTER ===")
    cleaned = clean_document_text(test_text)
    print(repr(cleaned))
    print("\n=== FORMATTED ===")
    print(cleaned)

if __name__ == "__main__":
    test_cleaning()
