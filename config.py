import sys
import os

# --- Path Configuration (Absolute Paths) ---
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    # ASSETS and VENDOR are inside the bundle
    BASE_DIR = sys._MEIPASS
    # MODELS and OUTPUT should be outside the bundle, next to the executable
    WORK_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    WORK_DIR = BASE_DIR

# Define other paths based on the BASE_DIR/WORK_DIR
MODEL_DIR = os.path.join(WORK_DIR, "models")
ASSET_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(WORK_DIR, "output")
VENDOR_DIR = os.path.join(BASE_DIR, "vendor")

# Explicit path to the bundled Tesseract executable
TESSERACT_CMD = os.path.join(VENDOR_DIR, "tesseract", "tesseract.exe")


# --- Model Configuration ---
MODEL_DEFAULT_FILENAME = "Llama-3.2-1B-Instruct-Q4_K_M.gguf"
MODEL_DOWNLOAD_URL = "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
MODEL_SAVE_FILENAME = "Llama-3.2-1B-Instruct-Q4_K_M.gguf"


# --- LLM Settings ---
N_GPU_LAYERS = -1
MAX_TOKENS = 32768


# --- Application Information ---
APP_NAME = "DocuMind AI"
APP_VERSION = "1.0.0"