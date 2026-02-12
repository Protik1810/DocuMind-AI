import io
import pytesseract
from PIL import Image
import config

# Tell pytesseract where to find the Tesseract program
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

def extract_text_from_image(image_bytes):
    """
    Performs OCR on an image provided as bytes.
    """
    try:
        # Wrap the image bytes in a BytesIO stream for robustness
        image_stream = io.BytesIO(image_bytes)
        image = Image.open(image_stream)
        text = pytesseract.image_to_string(image, lang='eng')
        return text
    except pytesseract.TesseractNotFoundError as e:
        # This error is now handled by the dependency_checker,
        # but is kept here as a failsafe.
        print(f"Tesseract Not Found Error: {e}")
        raise e
    except Exception as e:
        print(f"An error occurred during OCR: {e}")
        return ""