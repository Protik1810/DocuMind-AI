# DocuMind AI

**DocuMind AI** is a powerful, offline-first document analysis suite that leverages advanced AI and OCR technologies to extract insights, summarize content, and process documents directly on your local machine.

Built with a modern **PyQt6** interface and powered by local quantitative models (via `llama-cpp-python`), DocuMind AI ensures your data stays private while delivering robust analysis capabilities. This application is the result of focused development on combining user-friendly design with deep learning capabilities.

---

## 🚀 Key Features

- **Local AI Power**: Runs Large Language Models (LLMs) locally (e.g., Llama 3.2 GGUF models) for complete privacy and offline functionality. No API keys needed!
- **Intelligent OCR**: Integrated **Tesseract OCR** engine accurately extracts text from scanned PDFs and images.
- **Advanced Analytics**: Utilizes **Spacy** for Natural Language Processing (NLP) to understand context and structure.
- **Multi-Format Support**: Seamlessly handles:
  - **PDFs** (Scanned & Digital)
  - **Images** (JPG, PNG)
  - **Text Files** (TXT)
- **Rich Extraction**:
  - Automatically extracts and saves images from PDFs.
  - Detects and processes tables within documents.
- **Hardware Acceleration**: Smart detection of **NVIDIA CUDA** GPUs for accelerated AI inference, with automatic fallback to optimized CPU processing.
- **User-Centric GUI**:
  - Drag-and-drop file interface.
  - Real-time progress tracking with detailed logs.
  - Adjustable parameters for **AI Creativity** and **OCR Precision**.
  - Dark-themed, responsive design.

---

## 🛠️ Installation & Setup

### Prerequisites

Ensure you have the following installed:

- **Python 3.10+**
- **Tesseract OCR**:
  - **Windows**: Download and install from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki). Ensure the installation path is added to your system Environment Variables.
  - **Linux**: `sudo apt install tesseract-ocr`
  - **macOS**: `brew install tesseract`

### Step-by-Step Guide

1.  **Clone the Repository**

    ```bash
<<<<<<< HEAD
    git clone https://github.com/Protik1810/DocuMind-AI.git
=======
    git clone https://github.com/yourusername/DocuMind-AI.git
>>>>>>> b2d9d095e5041ceb1e60a27eea127ee3d0dc8d5f
    cd DocuMind-AI
    ```

2.  **Set Up Virtual Environment (Recommended)**

    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Download Spacy Model**
    Required for NLP features:
    ```bash
    python -m spacy download en_core_web_sm
    ```

---

## 🖥️ Usage

1.  **Launch the Application**

    ```bash
    python main.py
    ```

2.  **First Run Setup**
    - On launch, the application checks for models in the `models/` directory.
    - If no model is found, use the built-in **Download Model** button to fetch a compatible GGUF model (e.g., Llama 3.2).

3.  **Analyzing Documents**
    - **Select File**: Drag & drop or browse to select your PDF, Image, or Text file.
    - **Configure**:
      - Adjust **OCR DPI** for scan quality vs. speed.
      - Set **AI Creativity** for generated summaries.
    - **Start**: Click "Start Analysis" and watch the progress dial.

4.  **View Results**
    - **AI Summary**: Read the generated insights.
    - **Raw Text**: View the full extracted text.
    - **Extracted Images**: Access images pulled from the document.
    - **Output Folder**: All results are saved in the `output/` directory.

---

## 📦 Building from Source / Executable

To package DocuMind AI as a standalone executable:

1.  **Install PyInstaller**

    ```bash
    pip install pyinstaller
    ```

2.  **Build the App**
    Use the included spec file for a configured build:
    ```bash
    pyinstaller documind.spec
    ```
    The executable will be available in the `dist/` folder.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📜 License

This project is licensed under the **GNU General Public License v3 (GPL-3.0)**. See the LICENSE file for details.

---

**Developed by Protik Das**
