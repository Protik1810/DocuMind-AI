import os
import sys
import subprocess
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QPushButton, QFileDialog, QTextEdit, QGroupBox, QMessageBox,
                             QLabel, QPlainTextEdit, QComboBox, QCheckBox, QTabWidget, 
                             QScrollArea, QStackedLayout, QProgressBar, QSlider, QListWidget)
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtCore import Qt, QThreadPool, pyqtSlot

import config
from src.gui.widgets import DropArea, DialProgressBar
from src.gui.model_dialog import ModelManagerDialog
from src.utils.helpers import detect_hardware
from src.utils.dependency_checker import check_tesseract_dependency, check_spacy_model
from src.utils.downloader import DownloadWorker
from src.processing.pipeline import AnalysisPipeline, AnalysisSignals
from src.processing.llm_handler import LLMHandler

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.setGeometry(100, 100, 1400, 900)
        self.setWindowIcon(QIcon(os.path.join(config.ASSET_DIR, "logo.png")))
        
        self.llm_handler = LLMHandler()
        
        self.threadpool = QThreadPool()
        self.analysis_worker = None
        self.active_model_name = config.MODEL_DEFAULT_FILENAME
        self.selected_files = []  # List for batch processing
        self.current_batch_index = 0  # Track current file in batch
        self.batch_summaries = []  # Store summaries for batch export
        self.batch_raw_texts = []  # Store raw texts for batch export
        
        self._create_menu_bar()
        self._init_ui()
        self._setup_hardware_indicator()
        
        self.check_dependencies()
        self.check_model_file()

    def check_dependencies(self):
        is_found, message = check_tesseract_dependency()
        if not is_found:
            QMessageBox.warning(self, "Dependency Missing", message)
        is_found, message = check_spacy_model()
        if not is_found:
            QMessageBox.warning(self, "Dependency Missing", message)

    def check_model_file(self):
        self.model_combo.clear()
        
        # Check if the models directory exists
        if not os.path.exists(config.MODEL_DIR):
            os.makedirs(config.MODEL_DIR)
            
        # Scan for GGUF files
        models = [f for f in os.listdir(config.MODEL_DIR) if f.endswith(".gguf")]
        
        if models:
            self.model_combo.addItems(models)
            # Try to set default model if available
            if config.MODEL_SAVE_FILENAME in models:
                self.model_combo.setCurrentText(config.MODEL_SAVE_FILENAME)
                self.active_model_name = config.MODEL_SAVE_FILENAME
            else:
                self.active_model_name = models[0]
                self.model_combo.setCurrentText(models[0])

            self.download_widget_container.hide()
            self.model_combo.show()
            self.log_output.appendPlainText(f"✅ Local models found: {', '.join(models)}")
        else:
            self.download_widget_container.show()
            self.download_stack.setCurrentIndex(0)
            self.model_combo.hide()
            self.log_output.appendPlainText(f"⚠️ No models found. Please download the Llama 3.2 model.")

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        open_action = QAction("&Open Document(s)...", self)
        open_action.triggered.connect(self.select_files)
        file_menu.addAction(open_action)
        output_folder_action = QAction("Open &Output Folder", self)
        output_folder_action.triggered.connect(self.open_output_folder)
        file_menu.addAction(output_folder_action)
        file_menu.addSeparator()
        export_summary_action = QAction("Export &Summary...", self)
        export_summary_action.triggered.connect(lambda: self.export_results('summary'))
        file_menu.addAction(export_summary_action)
        export_raw_action = QAction("Export &Raw Text...", self)
        export_raw_action.triggered.connect(lambda: self.export_results('raw'))
        file_menu.addAction(export_raw_action)
        export_all_action = QAction("Export &All Results...", self)
        export_all_action.triggered.connect(lambda: self.export_results('all'))
        file_menu.addAction(export_all_action)
        file_menu.addSeparator()
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        models_menu = menu_bar.addMenu("&Models")
        manage_action = QAction("&Manage Models...", self)
        manage_action.triggered.connect(self.open_model_manager)
        models_menu.addAction(manage_action)
        about_menu = menu_bar.addMenu("&About")
        about_action = QAction("&About DocuMind AI", self)
        about_action.triggered.connect(self.show_about_dialog)
        about_menu.addAction(about_action)

    def _init_ui(self):
        self.top_bar_layout = QHBoxLayout()
        title = QLabel(config.APP_NAME)
        title.setObjectName("titleLabel")
        self.top_bar_layout.addWidget(title)
        self.top_bar_layout.addStretch()
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        upload_box = self._create_upload_box()
        controls_box = self._create_controls_box()
        config_box = self._create_config_box()
        progress_box = self._create_progress_box()
        output_tabs = self._create_output_tabs()
        grid.addWidget(upload_box, 0, 0)
        grid.addWidget(controls_box, 1, 0)
        grid.addWidget(config_box, 2, 0)
        grid.addWidget(progress_box, 0, 1)
        grid.addWidget(output_tabs, 1, 1, 2, 1)
        main_layout = QVBoxLayout()
        main_layout.addLayout(self.top_bar_layout)
        main_layout.addLayout(grid)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def _create_upload_box(self):
        box = QGroupBox("Document Upload")
        layout = QVBoxLayout(box)
        self.drop_area = DropArea()
        self.drop_area.dropped.connect(self.handle_files)
        browse_btn = QPushButton("Browse Files")
        browse_btn.clicked.connect(self.select_files)
        self.file_list_widget = QListWidget()
        self.file_list_widget.setAlternatingRowColors(True)
        self.file_list_widget.setMaximumHeight(120)
        layout.addWidget(self.drop_area)
        layout.addWidget(browse_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.file_list_widget)
        return box

    def _create_controls_box(self):
        box = QGroupBox("Analysis Controls")
        layout = QHBoxLayout(box)
        self.start_btn = QPushButton("Start Analysis")
        self.start_btn.setObjectName("startButton")
        self.start_btn.clicked.connect(self.start_analysis)
        self.stop_btn = QPushButton("Stop Analysis")
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_analysis)
        return box

    def _create_config_box(self):
        box = QGroupBox("AI Configuration")
        primary_layout = QVBoxLayout(box)
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("AI Model:"))
        self.model_combo = QComboBox()
        self.download_widget_container = QWidget()
        self.download_stack = QStackedLayout(self.download_widget_container)
        self.download_stack.setContentsMargins(0, 0, 0, 0)
        self.model_download_button = QPushButton("Download Model")
        self.model_download_button.clicked.connect(self.start_model_download)
        self.model_download_progress = QProgressBar()
        self.model_download_progress.setRange(0, 100)
        self.model_download_progress.setValue(0)
        self.model_download_progress.setTextVisible(True)
        self.model_download_progress.setFormat("%p%")
        self.model_download_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.download_stack.addWidget(self.model_download_button)
        self.download_stack.addWidget(self.model_download_progress)
        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.download_widget_container)
        primary_layout.addLayout(model_layout)
        middle_row_layout = QHBoxLayout()
        options_layout = QVBoxLayout()
        options_layout.addWidget(QLabel("Processing Options:"))
        self.ocr_check = QCheckBox("OCR Text Extraction")
        self.ocr_check.setChecked(True)
        self.img_check = QCheckBox("Image Extraction")
        self.tbl_check = QCheckBox("Table Extraction")
        self.nlp_check = QCheckBox("NLP Processing")
        self.nlp_check.setChecked(True)
        options_layout.addWidget(self.ocr_check)
        options_layout.addWidget(self.img_check)
        options_layout.addWidget(self.tbl_check)
        options_layout.addWidget(self.nlp_check)
        options_layout.addStretch()
        sliders_layout = QVBoxLayout()
        ocr_precision_label = QLabel("OCR DPI: 200")
        sliders_layout.addWidget(ocr_precision_label)
        self.ocr_slider = QSlider(Qt.Orientation.Horizontal)
        self.ocr_slider.setMinimum(100)
        self.ocr_slider.setMaximum(1200)
        self.ocr_slider.setValue(200)
        self.ocr_slider.setSingleStep(50)
        self.ocr_slider.setToolTip("Controls OCR scan resolution. Higher = more accurate but slower.")
        self.ocr_slider.valueChanged.connect(lambda v: ocr_precision_label.setText(f"OCR DPI: {v}"))
        sliders_layout.addWidget(self.ocr_slider)
        sliders_layout.addSpacing(10)
        ai_creativity_label = QLabel("AI Creativity: 20%")
        sliders_layout.addWidget(ai_creativity_label)
        self.ai_slider = QSlider(Qt.Orientation.Horizontal)
        self.ai_slider.setMinimum(0)
        self.ai_slider.setMaximum(100)
        self.ai_slider.setValue(20)
        self.ai_slider.setToolTip("Controls how creative/random the AI responses are. Lower = more factual, Higher = more creative.")
        self.ai_slider.valueChanged.connect(lambda v: ai_creativity_label.setText(f"AI Creativity: {v}%"))
        sliders_layout.addWidget(self.ai_slider)
        self.force_cpu_check = QCheckBox("Force CPU Mode (Bypass GPU)")
        self.force_cpu_check.setToolTip("Check this if you experience crashes on startup.")
        sliders_layout.addWidget(self.force_cpu_check)
        sliders_layout.addStretch()
        middle_row_layout.addLayout(options_layout)
        middle_row_layout.addLayout(sliders_layout)
        primary_layout.addLayout(middle_row_layout)
        primary_layout.addWidget(QLabel("User Instructions (Optional):"))
        self.instr_text = QTextEdit()
        self.instr_text.setMaximumHeight(80)
        primary_layout.addWidget(self.instr_text)
        return box

    def _create_progress_box(self):
        box = QGroupBox("Analysis Progress")
        main_layout = QHBoxLayout(box)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(10, 5, 10, 5)
        info_layout.addWidget(QLabel("Current File:"))
        self.current_file_label = QLabel("N/A")
        info_layout.addWidget(self.current_file_label)
        info_layout.addSpacing(10)
        info_layout.addWidget(QLabel("Document Type:"))
        self.doc_type_label = QLabel("N/A")
        info_layout.addWidget(self.doc_type_label)
        info_layout.addSpacing(10)
        info_layout.addWidget(QLabel("Pages:"))
        self.pages_processed_label = QLabel("0 / 0")
        info_layout.addWidget(self.pages_processed_label)
        info_layout.addSpacing(10)
        info_layout.addWidget(QLabel("Time / ETA:"))
        self.time_eta_label = QLabel("00:00 / 00:00")
        info_layout.addWidget(self.time_eta_label)
        info_layout.addSpacing(10)
        model_label_title = QLabel("Model:")
        model_label_title.setObjectName("infoTitle")
        self.model_in_use_label = QLabel("N/A")
        info_layout.addWidget(model_label_title)
        info_layout.addWidget(self.model_in_use_label)
        info_layout.addStretch()
        # Batch progress indicator
        self.batch_progress_label = QLabel("")
        info_layout.addWidget(self.batch_progress_label)
        self.batch_progress_bar = QProgressBar()
        self.batch_progress_bar.setRange(0, 100)
        self.batch_progress_bar.setValue(0)
        self.batch_progress_bar.setTextVisible(True)
        self.batch_progress_bar.setFormat("%p%")
        self.batch_progress_bar.hide()
        info_layout.addWidget(self.batch_progress_bar)
        info_layout.addStretch()
        self.progress_dial = DialProgressBar()
        main_layout.addLayout(info_layout, stretch=1)
        main_layout.addWidget(self.progress_dial, stretch=1)
        return box

    def _create_output_tabs(self):
        tabs = QTabWidget()
        self.summary_output = QTextEdit()
        self.summary_output.setReadOnly(True)
        self.raw_text_output = QPlainTextEdit()
        self.raw_text_output.setReadOnly(True)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        # --- Extracted Images Tab with Open Folder Button ---
        images_container = QWidget()
        images_container_layout = QVBoxLayout(images_container)
        images_container_layout.setContentsMargins(0, 0, 0, 0)
        open_folder_btn = QPushButton("📂 Open Output Folder")
        open_folder_btn.clicked.connect(self.open_output_folder)
        images_container_layout.addWidget(open_folder_btn)
        image_scroll_area = QScrollArea()
        image_scroll_area.setWidgetResizable(True)
        self.image_display_widget = QWidget()
        self.image_layout = QVBoxLayout(self.image_display_widget)
        image_scroll_area.setWidget(self.image_display_widget)
        images_container_layout.addWidget(image_scroll_area)
        tabs.addTab(self.summary_output, "AI Summary")
        tabs.addTab(self.raw_text_output, "Raw Text")
        tabs.addTab(images_container, "Extracted Images")
        tabs.addTab(self.log_output, "System Log")
        return tabs
        
    def _setup_hardware_indicator(self):
        hw_widget = QWidget()
        layout = QHBoxLayout(hw_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        self.device_logo_label = QLabel()
        self.device_text_label = QLabel("Detecting...")
        self.device_indicator_light = QLabel()
        self.device_indicator_light.setFixedSize(12, 12)
        
        device_type, device_name = detect_hardware()
        
        # Select brand logo based on device
        if device_type == 'cuda':
            text = f"Device: {device_name}"
            color = "#A3BE8C"
            if 'NVIDIA' in device_name.upper():
                logo_file = "nvidia_logo.png"
            elif 'INTEL' in device_name.upper():
                logo_file = "Intel_Core_2023_logo.png"
            elif 'AMD' in device_name.upper():
                logo_file = "amd_logo.png"
            else:
                logo_file = "nvidia_logo.png"  # Default for CUDA
        elif device_type == 'cpu':
            text = f"Device: {device_name}"
            if 'Intel' in device_name:
                logo_file = "Intel_Core_2023_logo.png"
                color = "#81A1C1"
            elif 'AMD' in device_name:
                logo_file = "amd_logo.png"
                color = "#D08770"
            else:
                logo_file = "logo.png"
                color = "#BF6A6A"
        else:
            text = "Device: Unknown"
            logo_file = "logo.png"
            color = "#BF6A6A"
        
        # Load brand logo
        logo_path = os.path.join(config.ASSET_DIR, logo_file)
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
        else:
            pixmap = QPixmap(os.path.join(config.ASSET_DIR, "logo.png"))
        
        # Scale to height 24, allow width to expand (maintain aspect ratio)
        self.device_logo_label.setPixmap(pixmap.scaledToHeight(24, Qt.TransformationMode.SmoothTransformation))
        
        layout.addWidget(self.device_logo_label)
        layout.addWidget(self.device_text_label)
        layout.addWidget(self.device_indicator_light)
        
        self.device_text_label.setText(text)
        self.device_indicator_light.setStyleSheet(f"QLabel {{ background-color: {color}; border: 1px solid {color}; border-radius: 6px; }}")
        self.top_bar_layout.addWidget(hw_widget)
    
    @pyqtSlot()
    def select_files(self):
        file_types = "All Supported Files (*.pdf *.jpg *.png *.txt);;All Files (*)"
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Document(s)", "", file_types)
        if file_paths:
            self.handle_files(file_paths)

    @pyqtSlot(list)
    def handle_files(self, file_paths):
        """Handle multiple file selection for batch processing."""
        self.selected_files = file_paths
        self.current_batch_index = 0
        self.batch_summaries = []
        self.batch_raw_texts = []
        
        self.file_list_widget.clear()
        for file_path in file_paths:
            self.file_list_widget.addItem(os.path.basename(file_path))
        
        # Update UI with first file info
        if file_paths:
            first_file = file_paths[0]
            filename = os.path.basename(first_file)
            ext = os.path.splitext(filename)[1].lower()
            doc_type_map = {'.pdf': "PDF", '.txt': "Text", '.jpg': "Image", '.png': "Image"}
            doc_type = doc_type_map.get(ext, "File")
            self.current_file_label.setText(filename)
            self.doc_type_label.setText(f"{doc_type} Document")
            
            if len(file_paths) > 1:
                self.log_output.setPlainText(f"Selected {len(file_paths)} files for batch analysis.\nFirst file: {filename}")
                self.batch_progress_label.setText(f"Batch: 0 / {len(file_paths)} files")
                self.batch_progress_bar.show()
            else:
                self.log_output.setPlainText(f"Selected file: {filename}")
                self.batch_progress_label.setText("")
                self.batch_progress_bar.hide()
        
        self.start_btn.setEnabled(True)

    @pyqtSlot()
    def start_analysis(self):
        active_model = self.model_combo.currentText()
        if not self.selected_files:
            QMessageBox.warning(self, "No File Selected", "Please select a document to analyze.")
            return
        if not active_model:
            QMessageBox.warning(self, "No Model", "No AI model selected. Please download a model first.")
            return
        
        # Reload model if it changed or hasn't been loaded yet
        if not self.llm_handler.process or self.llm_handler.model_name != active_model:
            try:
                if self.llm_handler.process:
                    self.llm_handler.shutdown()
                self.llm_handler.model_name = active_model
                force_cpu = self.force_cpu_check.isChecked()
                self.llm_handler.load_model(force_cpu=force_cpu)
            except RuntimeError as e:
                reply = QMessageBox.question(
                    self, 
                    "Model Missing", 
                    f"{str(e)}\n\nWould you like to download the model now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.start_model_download()
                return
            
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.model_in_use_label.setText(active_model)
        
        # Initialize batch state
        self.current_batch_index = 0
        self.batch_summaries = []
        self.batch_raw_texts = []
        
        # Update batch progress
        if len(self.selected_files) > 1:
            self.batch_progress_bar.show()
            self.batch_progress_bar.setValue(0)
        
        self.raw_text_output.clear()
        self.summary_output.clear()
        self.log_output.clear()
        
        # Start processing first file
        self._process_next_file()

    def _process_next_file(self):
        """Process the next file in the batch queue."""
        if self.current_batch_index >= len(self.selected_files):
            self._on_batch_complete()
            return
        
        file_path = self.selected_files[self.current_batch_index]
        filename = os.path.basename(file_path)
        total_files = len(self.selected_files)
        
        # Update UI
        self.current_file_label.setText(filename)
        ext = os.path.splitext(filename)[1].lower()
        doc_type_map = {'.pdf': "PDF", '.txt': "Text", '.jpg': "Image", '.png': "Image"}
        doc_type = doc_type_map.get(ext, "File")
        self.doc_type_label.setText(f"{doc_type} Document")
        
        if total_files > 1:
            self.batch_progress_label.setText(f"Batch: {self.current_batch_index + 1} / {total_files} files")
            batch_pct = int((self.current_batch_index / total_files) * 100)
            self.batch_progress_bar.setValue(batch_pct)
            self.log_output.appendPlainText(f"\n{'='*50}\nStarting file {self.current_batch_index + 1} of {total_files}: {filename}\n{'='*50}")
        
        # Get processing options
        temperature = self.ai_slider.value() / 100.0
        ocr_dpi = self.ocr_slider.value()
        proc_options = {
            'ocr': self.ocr_check.isChecked(),
            'images': self.img_check.isChecked(),
            'tables': self.tbl_check.isChecked(),
            'nlp': self.nlp_check.isChecked(),
            'temperature': temperature,
            'ocr_dpi': ocr_dpi
        }
        user_instr = self.instr_text.toPlainText()
        
        # Create and start analysis pipeline
        signals = AnalysisSignals()
        self.analysis_worker = AnalysisPipeline(file_path, user_instr, proc_options, self.llm_handler, signals)
        self.analysis_worker.signals.log.connect(self.log_output.appendPlainText)
        self.analysis_worker.signals.progress.connect(self.progress_dial.setValue)
        self.analysis_worker.signals.page_processed.connect(self.append_raw_text)
        self.analysis_worker.signals.summary_header.connect(self.on_summary_header)
        self.analysis_worker.signals.token_received.connect(self.on_token_received)
        self.analysis_worker.signals.page_summary_ready.connect(self.on_page_summary_done)
        self.analysis_worker.signals.detailed_progress.connect(self.update_progress_info)
        self.analysis_worker.signals.status_changed.connect(self.progress_dial.setState)
        self.analysis_worker.signals.finished.connect(self.on_file_analysis_finished)
        self.analysis_worker.signals.error.connect(self.on_file_analysis_error)
        self.threadpool.start(self.analysis_worker)

    @pyqtSlot(str)
    def on_file_analysis_finished(self, final_report):
        """Handle completion of a single file in the batch."""
        # Store results for export
        self.batch_summaries.append(final_report)
        self.batch_raw_texts.append(self.raw_text_output.toPlainText())
        
        self.current_batch_index += 1
        
        # Update batch progress
        if len(self.selected_files) > 1:
            batch_pct = int((self.current_batch_index / len(self.selected_files)) * 100)
            self.batch_progress_bar.setValue(batch_pct)
        
        # Process next file or complete batch
        if self.current_batch_index < len(self.selected_files):
            self._process_next_file()
        else:
            self._on_batch_complete()

    @pyqtSlot(str)
    def on_file_analysis_error(self, error_message):
        """Handle error for a single file in the batch."""
        self.summary_output.append(f"\n❌ Error processing file: {error_message}\n")
        self.log_output.appendPlainText(f"🔴 ERROR: {error_message}")
        
        # Move to next file
        self.current_batch_index += 1
        if self.current_batch_index < len(self.selected_files):
            self._process_next_file()
        else:
            self._on_batch_complete()

    def _on_batch_complete(self):
        """Handle completion of the entire batch."""
        self.summary_output.append("\n---\n✅ **Batch Analysis Complete!**")
        self.progress_dial.setState('ready')
        
        # Update batch progress
        if len(self.selected_files) > 1:
            self.batch_progress_bar.setValue(100)
            self.batch_progress_label.setText(f"Batch: {len(self.selected_files)} / {len(self.selected_files)} files completed")
        
        self.reset_controls()

    @pyqtSlot(str)
    def on_analysis_finished(self, final_report):
        """Legacy handler - kept for compatibility."""
        self.summary_output.append("\n---\n✅ **Analysis Complete!**")
        self.progress_dial.setState('ready')
        self.reset_controls()
        
    @pyqtSlot(str)
    def on_analysis_error(self, error_message):
        """Legacy handler - kept for compatibility."""
        QMessageBox.critical(self, "Analysis Error", error_message)
        self.progress_dial.setState('stopped')
        self.reset_controls()

    @pyqtSlot(int, int, str)
    def append_raw_text(self, page_num, total_pages, text):
        header = f"--- Page {page_num} of {total_pages} ---\n\n"
        self.raw_text_output.appendPlainText(header + text + "\n\n")

    @pyqtSlot(int, int)
    def on_summary_header(self, page_num, total_pages):
        """Inserts the header before streaming starts."""
        header = f"<h3>Summary for Page {page_num} of {total_pages}</h3>\n"
        self.summary_output.append(header)
        # Move cursor to the very end for token appending
        cursor = self.summary_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.summary_output.setTextCursor(cursor)

    @pyqtSlot(str)
    def on_token_received(self, token):
        """Appends a single token at the current cursor position."""
        cursor = self.summary_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(token)
        self.summary_output.setTextCursor(cursor)
        self.summary_output.ensureCursorVisible()

    @pyqtSlot(int, int, str)
    def on_page_summary_done(self, page_num, total_pages, summary_text):
        """Called when a full page summary is complete. Adds a separator."""
        self.summary_output.append("\n---\n")
        
    @pyqtSlot(int, int, str, str)
    def update_progress_info(self, pages_done, total_pages, elapsed_str, eta_str):
        self.pages_processed_label.setText(f"{pages_done} / {total_pages}")
        self.time_eta_label.setText(f"{elapsed_str} / {eta_str}")
        
    @pyqtSlot()
    def stop_analysis(self):
        if self.analysis_worker:
            self.analysis_worker.stop()
            self.log_output.appendPlainText("🛑 Analysis stop requested...")
            self.stop_btn.setEnabled(False)

    def reset_controls(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.model_in_use_label.setText("N/A")
        self.analysis_worker = None
    
    # --- Export Functionality ---
    
    @pyqtSlot()
    def export_results(self, export_type='all'):
        """Export analysis results to files.
        
        Args:
            export_type: 'summary', 'raw', or 'all'
        """
        if not self.batch_summaries and not self.batch_raw_texts:
            QMessageBox.information(self, "No Results", "No analysis results to export. Run an analysis first.")
            return
        
        # Get save location
        file_types = {
            'summary': "Markdown Files (*.md);;HTML Files (*.html);;Text Files (*.txt)",
            'raw': "Text Files (*.txt)",
            'all': "Markdown Files (*.md);;HTML Files (*.html);;Text Files (*.txt)"
        }
        
        default_filename = {
            'summary': "documind_summary",
            'raw': "documind_raw_text",
            'all': "documind_report"
        }
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            f"Export {export_type.title()} Results",
            os.path.join(config.OUTPUT_DIR, default_filename.get(export_type, "documind_export")),
            file_types.get(export_type, "All Files (*)")
        )
        
        if not file_path:
            return
        
        # Determine extension and format
        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            # Add extension based on filter
            if "Markdown" in selected_filter:
                ext = ".md"
                file_path += ext
            elif "HTML" in selected_filter:
                ext = ".html"
                file_path += ext
            else:
                ext = ".txt"
                file_path += ext
        
        try:
            if export_type == 'summary':
                self._export_summary(file_path, ext)
            elif export_type == 'raw':
                self._export_raw_text(file_path)
            else:  # all
                self._export_all(file_path, ext)
            
            QMessageBox.information(self, "Export Complete", f"Results exported to:\n{file_path}")
            self.log_output.appendPlainText(f"📁 Results exported to: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export results:\n{str(e)}")

    def _export_summary(self, file_path, ext):
        """Export summary results in the specified format."""
        combined_summary = "\n\n---\n\n".join(self.batch_summaries)
        
        if ext == '.md':
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {config.APP_NAME} - Analysis Summary\n\n")
                f.write(f"Generated on: {self._get_timestamp()}\n\n")
                f.write("## Results\n\n")
                f.write(combined_summary)
        elif ext == '.html':
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{config.APP_NAME} - Analysis Summary</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; }}
        .timestamp {{ color: #888; font-style: italic; }}
        .summary {{ line-height: 1.6; }}
    </style>
</head>
<body>
    <h1>{config.APP_NAME} - Analysis Summary</h1>
    <p class="timestamp">Generated on: {self._get_timestamp()}</p>
    <div class="summary">
        {combined_summary.replace(chr(10), '<br>')}
    </div>
</body>
</html>""")
        else:  # .txt
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"{config.APP_NAME} - Analysis Summary\n")
                f.write(f"{'='*50}\n")
                f.write(f"Generated on: {self._get_timestamp()}\n\n")
                f.write(combined_summary)

    def _export_raw_text(self, file_path):
        """Export raw extracted text."""
        combined_text = "\n\n".join(self.batch_raw_texts)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(combined_text)

    def _export_all(self, file_path, ext):
        """Export complete report with summary and raw text."""
        combined_summary = "\n\n---\n\n".join(self.batch_summaries)
        combined_text = "\n\n".join(self.batch_raw_texts)
        
        if ext == '.md':
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {config.APP_NAME} - Complete Report\n\n")
                f.write(f"Generated on: {self._get_timestamp()}\n\n")
                f.write("## AI Summary\n\n")
                f.write(combined_summary)
                f.write("\n\n## Raw Extracted Text\n\n")
                f.write(combined_text)
        elif ext == '.html':
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{config.APP_NAME} - Complete Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
        .timestamp {{ color: #888; font-style: italic; }}
        .section {{ margin-bottom: 30px; }}
        pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>{config.APP_NAME} - Complete Report</h1>
    <p class="timestamp">Generated on: {self._get_timestamp()}</p>
    
    <div class="section">
        <h2>AI Summary</h2>
        {combined_summary.replace(chr(10), '<br>')}
    </div>
    
    <div class="section">
        <h2>Raw Extracted Text</h2>
        <pre>{combined_text}</pre>
    </div>
</body>
</html>""")
        else:  # .txt
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"{config.APP_NAME} - Complete Report\n")
                f.write(f"{'='*50}\n")
                f.write(f"Generated on: {self._get_timestamp()}\n\n")
                f.write("AI SUMMARY\n")
                f.write("-"*30 + "\n")
                f.write(combined_summary)
                f.write("\n\nRAW EXTRACTED TEXT\n")
                f.write("-"*30 + "\n")
                f.write(combined_text)

    def _get_timestamp(self):
        """Get formatted timestamp for exports."""
        import time
        return time.strftime("%Y-%m-%d %H:%M:%S")

    @pyqtSlot()
    def open_model_manager(self):
        current_model = self.model_combo.currentText()
        dialog = ModelManagerDialog(current_model, self)
        dialog.model_changed.connect(self.on_model_changed)
        dialog.exec()
        self.check_model_file()
        
    @pyqtSlot(str)
    def on_model_changed(self, new_model_name):
        if self.model_combo.findText(new_model_name) == -1:
             self.model_combo.addItem(new_model_name)
        self.model_combo.setCurrentText(new_model_name)
        self.active_model_name = new_model_name
        
    @pyqtSlot()
    def start_model_download(self):
        self.download_stack.setCurrentIndex(1)
        self.log_output.appendPlainText(f"⬇️ Starting download...")
        save_path = os.path.join(config.MODEL_DIR, config.MODEL_SAVE_FILENAME)
        worker = DownloadWorker(config.MODEL_DOWNLOAD_URL, save_path)
        worker.signals.progress.connect(self.model_download_progress.setValue)
        worker.signals.finished.connect(self.on_download_finished)
        worker.signals.error.connect(self.on_download_error)
        self.threadpool.start(worker)

    @pyqtSlot()
    def on_download_finished(self):
        self.log_output.appendPlainText("✅ Download complete!")
        self.check_model_file()

    @pyqtSlot(str)
    def on_download_error(self, error_msg):
        QMessageBox.critical(self, "Download Error", f"Failed to download model.\n\nError: {error_msg}")
        self.download_stack.setCurrentIndex(0)
        self.model_download_button.setText("Retry Download")

    @pyqtSlot()
    def show_about_dialog(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"About {config.APP_NAME}")
        pixmap = QPixmap(os.path.join(config.ASSET_DIR, "logo.png"))
        msg_box.setIconPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        about_text = (
            f"<h3>{config.APP_NAME}</h3><p>Version {config.APP_VERSION}</p>"
            "<p><b>Developed by Protik Das</b></p>"
            "<p>A modern OCR and NLP analysis suite.</p>"
            "<p>This application is released under the <a href='https://www.gnu.org/licenses/gpl-3.0.html'>GNU General Public License v3</a>.</p>"
        )
        msg_box.setText(about_text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    @pyqtSlot()
    def open_output_folder(self):
        if not os.path.exists(config.OUTPUT_DIR):
            os.makedirs(config.OUTPUT_DIR)
        if sys.platform == "win32":
            os.startfile(os.path.realpath(config.OUTPUT_DIR))
        elif sys.platform == "darwin":
            subprocess.run(["open", os.path.realpath(config.OUTPUT_DIR)])
        else:
            subprocess.run(["xdg-open", os.path.realpath(config.OUTPUT_DIR)])
            
    def closeEvent(self, event):
        """Ensures running analysis and model are terminated when the app closes."""
        if self.analysis_worker:
            self.analysis_worker.stop()
        self.llm_handler.shutdown()
        event.accept()
