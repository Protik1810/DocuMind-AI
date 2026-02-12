# src/processing/nlp_handler.py

from collections import defaultdict

# Lazy-load spaCy to avoid crash if not installed
_nlp = None
_nlp_loaded = False


def _get_nlp():
    """Loads the spaCy model lazily on first use."""
    global _nlp, _nlp_loaded
    if not _nlp_loaded:
        _nlp_loaded = True
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError) as e:
            print(f"spaCy not available: {e}")
            _nlp = None
    return _nlp


def process_text(text: str) -> str:
    """
    Processes text using spaCy to extract named entities and returns them
    as a formatted string.

    Args:
        text: The raw text to analyze.

    Returns:
        A formatted string of extracted entities, grouped by type.
    """
    nlp = _get_nlp()
    if not nlp:
        return "spaCy model not loaded. Cannot perform NLP analysis."

    doc = nlp(text)

    entities = defaultdict(list)
    for ent in doc.ents:
        # Avoid adding duplicate entities within the same category
        if ent.text.strip() not in entities[ent.label_]:
            entities[ent.label_].append(ent.text.strip())

    if not entities:
        return "No named entities found."

    # Format the entities into a clean string for the LLM prompt
    formatted_output = "Key Entities Found:\n"
    for label, items in entities.items():
        formatted_output += f"- {label}: {', '.join(items)}\n"

    return formatted_output