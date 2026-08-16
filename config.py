import sys
import os
import platform
import shutil

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

# --- Cross-platform Tesseract Path Detection ---
def _find_tesseract():
    """
    Locate the Tesseract executable in a cross-platform manner.
    Priority:
    1. Bundled vendor/tesseract (Windows portable)
    2. shutil.which() (system PATH lookup)
    3. Common installation paths per platform
    4. Fallback to platform-specific default
    """
    system = platform.system()
    
    # 1. Check for bundled vendor version (Windows portable)
    bundled_paths = []
    if system == "Windows":
        bundled_paths.append(os.path.join(VENDOR_DIR, "tesseract", "tesseract.exe"))
    else:
        bundled_paths.append(os.path.join(VENDOR_DIR, "tesseract", "tesseract"))
    
    for bundled in bundled_paths:
        if os.path.exists(bundled):
            return bundled
    
    # 2. Try system PATH via shutil.which
    system_cmd = shutil.which("tesseract")
    if system_cmd:
        return system_cmd
    
    # 3. Platform-specific common paths
    if system == "Windows":
        # Windows: Check Program Files
        prog_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        prog_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        win_paths = [
            os.path.join(prog_files, "Tesseract-OCR", "tesseract.exe"),
            os.path.join(prog_files_x86, "Tesseract-OCR", "tesseract.exe"),
        ]
        for p in win_paths:
            if os.path.exists(p):
                return p
    elif system == "Darwin":
        # macOS: Homebrew paths
        mac_paths = [
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
        ]
        for p in mac_paths:
            if os.path.exists(p):
                return p
    else:
        # Linux: Standard paths
        linux_paths = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
        ]
        for p in linux_paths:
            if os.path.exists(p):
                return p
    
    # 4. Fallback to platform-specific default
    if system == "Windows":
        return os.path.join(VENDOR_DIR, "tesseract", "tesseract.exe")
    else:
        return "/usr/bin/tesseract"


TESSERACT_CMD = _find_tesseract()


# --- Model Configuration ---
MODEL_DEFAULT_FILENAME = "Llama-3.2-1B-Instruct-Q4_K_M.gguf"
MODEL_DOWNLOAD_URL = "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
MODEL_SAVE_FILENAME = "Llama-3.2-1B-Instruct-Q4_K_M.gguf"


# --- LLM Settings ---
N_GPU_LAYERS = -1
MAX_TOKENS = 32768


# --- Application Information ---
APP_NAME = "DocuMind AI"
APP_VERSION = "1.1.0"
