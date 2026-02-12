# main.py

import sys
import os
import multiprocessing
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
import config # Now contains our absolute paths

def main():
    """Application entry point."""
    # Use the absolute path for the models directory
    if not os.path.exists(config.MODEL_DIR):
        os.makedirs(config.MODEL_DIR)

    app = QApplication(sys.argv)

    # Use the absolute path for the stylesheet
    stylesheet_path = os.path.join(config.ASSET_DIR, "styles.qss")
    try:
        with open(stylesheet_path, "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Stylesheet not found. Using default styles.")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()