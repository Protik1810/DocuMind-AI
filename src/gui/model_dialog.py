# src/gui/model_dialog.py

import os
import re
from urllib.parse import urlparse, unquote
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QVBoxLayout, QTabWidget, 
                             QWidget, QListWidget, QPushButton, QHBoxLayout,
                             QLineEdit, QProgressBar, QMessageBox, QLabel)
from PyQt6.QtCore import pyqtSignal, QThreadPool

import config
from src.utils.downloader import DownloadWorker

# Trusted domains for model downloads
TRUSTED_DOMAINS = [
    'huggingface.co',
    'github.com',
    'raw.githubusercontent.com',
    'objects.githubusercontent.com',
]

class ModelManagerDialog(QDialog):
    """A dialog for managing local and downloadable AI models."""
    # Signal to notify the main window that the active model has changed
    model_changed = pyqtSignal(str)

    def __init__(self, active_model, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Model Manager")
        self.setMinimumSize(600, 400)
        self.active_model = active_model
        self.threadpool = QThreadPool()

        # --- Main Layout ---
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # --- Create Tabs ---
        manage_tab = self._create_manage_tab()
        download_tab = self._create_download_tab()
        tabs.addTab(manage_tab, "Manage Local Models")
        tabs.addTab(download_tab, "Download New Model")

        # --- Dialog Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_manage_tab(self):
        """Creates the tab for managing locally stored models."""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Left side: List of models
        self.model_list = QListWidget()
        self.refresh_model_list()
        layout.addWidget(self.model_list)

        # Right side: Action buttons
        button_layout = QVBoxLayout()
        set_active_btn = QPushButton("Set as Active")
        set_active_btn.clicked.connect(self.set_active_model)
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_model)
        button_layout.addWidget(set_active_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        return widget

    def _create_download_tab(self):
        """Creates the tab for downloading new models."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Enter direct GGUF model download URL:"))
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://huggingface.co/.../model.gguf")
        layout.addWidget(self.url_input)

        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.start_download)
        layout.addWidget(self.download_button)

        self.download_progress = QProgressBar()
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        self.download_progress.setTextVisible(True)
        self.download_progress.setFormat("%p%")
        self.download_progress.hide() # Hidden by default
        layout.addWidget(self.download_progress)
        
        layout.addStretch()
        return widget

    def refresh_model_list(self):
        """Scans the models directory and updates the list widget."""
        self.model_list.clear()
        if not os.path.exists(config.MODEL_DIR):
            os.makedirs(config.MODEL_DIR)
        
        models = [f for f in os.listdir(config.MODEL_DIR) if f.endswith(".gguf")]
        for model_file in models:
            self.model_list.addItem(model_file)
            if model_file == self.active_model:
                self.model_list.setCurrentRow(self.model_list.count() - 1)

    def set_active_model(self):
        selected_item = self.model_list.currentItem()
        if selected_item:
            model_name = selected_item.text()
            self.model_changed.emit(model_name)
            self.active_model = model_name
            QMessageBox.information(self, "Success", f"'{model_name}' is now the active model.")
    
    def delete_model(self):
        selected_item = self.model_list.currentItem()
        if not selected_item:
            return
            
        model_name = selected_item.text()
        
        # [SECURITY] Validate path stays within MODEL_DIR
        target_path = os.path.abspath(os.path.join(config.MODEL_DIR, model_name))
        if not target_path.startswith(os.path.abspath(config.MODEL_DIR)):
            QMessageBox.critical(self, "Security Error", "Invalid model path detected.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to permanently delete '{model_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(target_path)
                self.refresh_model_list()
                QMessageBox.information(self, "Success", f"Deleted '{model_name}'.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete file: {e}")

    def start_download(self):
        url = self.url_input.text().strip()
        
        # [SECURITY] Validate URL scheme (HTTPS only)
        if not url.startswith("https://") or not url.endswith(".gguf"):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid HTTPS URL to a .gguf file.")
            return
        
        # [SECURITY] Validate domain against whitelist
        parsed = urlparse(url)
        if not any(parsed.hostname and parsed.hostname.endswith(domain) for domain in TRUSTED_DOMAINS):
            reply = QMessageBox.warning(
                self, "Untrusted Source",
                f"The domain '{parsed.hostname}' is not in the trusted sources list.\n\n"
                f"Trusted sources: {', '.join(TRUSTED_DOMAINS)}\n\n"
                "Do you want to proceed anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # [SECURITY] Sanitize filename from URL to prevent path traversal
        raw_filename = os.path.basename(unquote(parsed.path))
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '', raw_filename)
        if not safe_filename or not safe_filename.endswith('.gguf'):
            safe_filename = 'downloaded_model.gguf'
        
        save_path = os.path.join(config.MODEL_DIR, safe_filename)
        
        # [SECURITY] Ensure save path is within MODEL_DIR
        if not os.path.abspath(save_path).startswith(os.path.abspath(config.MODEL_DIR)):
            QMessageBox.critical(self, "Security Error", "Invalid save path detected.")
            return

        self.download_button.hide()
        self.download_progress.show()

        worker = DownloadWorker(url, save_path)
        worker.signals.progress.connect(self.download_progress.setValue)
        worker.signals.finished.connect(self.on_download_finished)
        worker.signals.error.connect(self.on_download_error)
        self.threadpool.start(worker)

    def on_download_finished(self):
        QMessageBox.information(self, "Success", "Model downloaded successfully.")
        self.download_progress.hide()
        self.download_button.show()
        self.url_input.clear()
        self.refresh_model_list()

    def on_download_error(self, error_msg):
        QMessageBox.critical(self, "Download Error", f"Failed to download model.\n\nError: {error_msg}")
        self.download_progress.hide()
        self.download_button.show()