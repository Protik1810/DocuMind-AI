import os
import time
import fitz
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable

from . import ocr_handler
from . import nlp_handler
import config

class AnalysisSignals(QObject):
    finished = pyqtSignal(str)
    progress = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    page_processed = pyqtSignal(int, int, str)
    page_summary_ready = pyqtSignal(int, int, str)
    summary_header = pyqtSignal(int, int)
    token_received = pyqtSignal(str)
    detailed_progress = pyqtSignal(int, int, str, str)
    log = pyqtSignal(str)
    error = pyqtSignal(str)

class AnalysisPipeline(QRunnable):
    def __init__(self, file_path, user_instructions, processing_options, llm_handler, signals):
        super().__init__()
        self.file_path = file_path
        self.user_instructions = user_instructions
        self.processing_options = processing_options
        self.llm_handler = llm_handler
        self.signals = signals
        self._is_running = True

    def stop(self):
        self._is_running = False

    def _create_output_folder(self):
        if not os.path.exists(config.OUTPUT_DIR): os.makedirs(config.OUTPUT_DIR)
        
        # [SECURITY] Sanitize filename to prevent Path Traversal and invalid characters
        # Allow alphanumeric, spaces, dashes, underscores, dots. Strip everything else.
        import re
        base_name = os.path.basename(self.file_path)
        # Remove any path separators or control characters
        clean_name = re.sub(r'[^a-zA-Z0-9 _\-\.]', '', base_name)
        # Remove leading dots to prevent hiding files or .. up-level references
        clean_name = re.sub(r'^\.+', '', clean_name)
        
        if not clean_name: clean_name = "doc_analysis"
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        folder_name = f"{clean_name}_{timestamp}"
        
        # [SECURITY] Ensure final path is strictly within OUTPUT_DIR
        output_path = os.path.join(config.OUTPUT_DIR, folder_name)
        output_path = os.path.abspath(output_path)
        if not output_path.startswith(os.path.abspath(config.OUTPUT_DIR)):
             raise ValueError(f"Security Error: Output path traversal detected: {output_path}")
             
        os.makedirs(output_path)
        return output_path

    def run(self):
        doc = None
        try:
            start_time = time.time()
            self.signals.log.emit(f"▶️ Analysis started for: {os.path.basename(self.file_path)}")
            
            output_path = self._create_output_folder()
            self.signals.log.emit(f"📂 Created output folder: {os.path.basename(output_path)}")
            self.signals.log.emit(f"✅ AI engine is running in a separate process.")
            
            self.signals.status_changed.emit('analyzing')
            
            try:
                doc = fitz.open(self.file_path)
            except Exception as e:
                raise RuntimeError(f"Failed to open document: {e}\nThe file may be corrupt or in an unsupported format.")
            
            total_pages = len(doc)
            if total_pages == 0:
                raise RuntimeError("Document contains 0 pages. Nothing to analyze.")
            self.signals.log.emit(f"✅ Detected {total_pages} pages. Starting page-by-page analysis...")
            final_summary_parts = []
            full_raw_text = ""

            # Each page has 5 sub-steps for smooth progress
            SUB_STEPS = 5  # OCR, Images, Tables, NLP, AI Summary
            total_steps = total_pages * SUB_STEPS

            for i, page in enumerate(doc):
                if not self._is_running:
                    self.signals.log.emit("🛑 Process stopped by user.")
                    break

                current_page = i + 1
                base_step = (i) * SUB_STEPS  # completed steps from previous pages
                self.signals.log.emit(f"--- Processing Page {current_page}/{total_pages} ---")
                
                elapsed_seconds = time.time() - start_time
                elapsed_time_str = time.strftime("%M:%S", time.gmtime(elapsed_seconds))
                time_per_page = elapsed_seconds / current_page if i > 0 else 0
                eta_str = time.strftime("%M:%S", time.gmtime((total_pages - current_page) * time_per_page)) if i > 0 else "..."
                self.signals.detailed_progress.emit(current_page, total_pages, elapsed_time_str, eta_str)

                # --- Sub-step 1: OCR / Text Extraction ---
                ocr_dpi = self.processing_options.get('ocr_dpi', 200)
                if self.processing_options.get('ocr', True):
                    self.signals.log.emit(f"  > OCR (DPI: {ocr_dpi})...")
                    pix = page.get_pixmap(dpi=ocr_dpi)
                    page_text = ocr_handler.extract_text_from_image(pix.tobytes("png"))
                else:
                    self.signals.log.emit(f"  > Extracting Text...")
                    page_text = page.get_text()
                
                self.signals.progress.emit(int(((base_step + 1) / total_steps) * 100))
                
                full_raw_text += f"--- Page {current_page} ---\n{page_text}\n\n"
                self.signals.page_processed.emit(current_page, total_pages, page_text)

                # --- Sub-step 2: Image Extraction ---
                if self.processing_options.get('images', False):
                    self.signals.log.emit(f"  > Extracting Images...")
                    image_list = page.get_images(full=True)
                    if image_list:
                         self.signals.log.emit(f"    - Found {len(image_list)} images.")
                         for img_index, img in enumerate(image_list, start=1):
                             xref = img[0]
                             base_image = doc.extract_image(xref)
                             image_bytes = base_image["image"]
                             image_ext = base_image["ext"]
                             img_filename = f"page_{current_page}_img_{img_index}.{image_ext}"
                             img_filepath = os.path.join(output_path, img_filename)
                             with open(img_filepath, "wb") as f:
                                 f.write(image_bytes)
                    else:
                         self.signals.log.emit(f"    - No embedded images. Saving page render.")
                         img_path = os.path.join(output_path, f"page_{current_page}_render.png")
                         pix = page.get_pixmap(dpi=ocr_dpi)
                         pix.save(img_path)
                self.signals.progress.emit(int(((base_step + 2) / total_steps) * 100))

                # --- Sub-step 3: Table Extraction ---
                if self.processing_options.get('tables', False):
                     try:
                        tables = page.find_tables()
                        if tables.tables:
                             self.signals.log.emit(f"  > Extracting Tables ({len(tables.tables)} found)...")
                             for table_index, table in enumerate(tables.tables, start=1):
                                 df = table.to_pandas()
                                 csv_filename = f"page_{current_page}_table_{table_index}.csv"
                                 csv_path = os.path.join(output_path, csv_filename)
                                 df.to_csv(csv_path, index=False)
                                 self.signals.log.emit(f"    - Saved: {csv_filename}")
                     except Exception as e:
                         self.signals.log.emit(f"    ⚠️ Table extraction failed (or not supported): {e}")
                self.signals.progress.emit(int(((base_step + 3) / total_steps) * 100))

                # --- Sub-step 4: NLP ---
                page_nlp_data = ""
                if self.processing_options.get('nlp', True):
                    self.signals.log.emit(f"  > NLP Analysis...")
                    page_nlp_data = nlp_handler.process_text(page_text)
                self.signals.progress.emit(int(((base_step + 4) / total_steps) * 100))

                # --- Sub-step 5: AI Summarization (Streaming) ---
                self.signals.log.emit(f"  > AI Summarization...")
                self.signals.summary_header.emit(current_page, total_pages)
                
                temperature = self.processing_options.get('temperature', 0.2)
                page_summary_tokens = []
                token_count = 0
                # Progress within AI step: interpolate from sub-step 4 to sub-step 5
                ai_start_pct = ((base_step + 4) / total_steps) * 100
                ai_end_pct = ((base_step + 5) / total_steps) * 100
                max_expected_tokens = 512  # matches max_tokens in LLM call
                
                for token in self.llm_handler.generate_summary_stream(page_text, page_nlp_data, self.user_instructions, temperature):
                    if not self._is_running:
                        break
                    page_summary_tokens.append(token)
                    self.signals.token_received.emit(token)
                    token_count += 1
                    # Update progress every 5 tokens during streaming
                    if token_count % 5 == 0:
                        token_fraction = min(token_count / max_expected_tokens, 1.0)
                        current_pct = int(ai_start_pct + (ai_end_pct - ai_start_pct) * token_fraction)
                        self.signals.progress.emit(current_pct)
                
                page_summary = "".join(page_summary_tokens)
                self.signals.page_summary_ready.emit(current_page, total_pages, page_summary)
                final_summary_parts.append(f"## Page {current_page} Summary\n{page_summary}")
                
                self.signals.progress.emit(int(((base_step + 5) / total_steps) * 100))

            text_path = os.path.join(output_path, "raw_text.txt")
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(full_raw_text)

            self.signals.log.emit("🏁 Analysis complete. Finalizing report.")
            final_report = "\n\n".join(final_summary_parts)
            self.signals.finished.emit(final_report)

        except Exception as e:
            self.signals.error.emit(str(e))
            self.signals.log.emit(f"🔴 ERROR: {e}")
        finally:
            if doc:
                doc.close()