import os
import config


def check_tesseract_dependency():
    """
    Checks if the bundled Tesseract executable exists at the specified path.
    """
    if os.path.exists(config.TESSERACT_CMD):
        return True, "Bundled Tesseract OCR is available."

    message = (
        f"Bundled Tesseract OCR not found.\n\n"
        f"The application expected to find it at:\n{config.TESSERACT_CMD}\n\n"
        "Please ensure the 'vendor/tesseract' directory exists and contains the "
        "unzipped portable Tesseract program files."
    )
    return False, message


def check_spacy_model():
    """
    Checks if the spaCy model is installed.
    Imports spacy lazily to avoid crash if not installed.
    """
    try:
        import spacy
        spacy.load("en_core_web_sm")
        return True, "spaCy model 'en_core_web_sm' is available."
    except ImportError:
        message = (
            "spaCy library is not installed.\n\n"
            "Please install it by running:\n\n"
            "pip install spacy\n"
            "python -m spacy download en_core_web_sm"
        )
        return False, message
    except OSError:
        message = (
            "spaCy model 'en_core_web_sm' not found.\n\n"
            "Please install it by running the following command in your terminal:\n\n"
            "python -m spacy download en_core_web_sm"
        )
        return False, message