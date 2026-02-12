# src/utils/downloader.py

import os
import requests
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable


class DownloadSignals(QObject):
    """Defines signals for the downloader."""
    progress = pyqtSignal(int)  # Emits download percentage
    finished = pyqtSignal()
    error = pyqtSignal(str)


class DownloadWorker(QRunnable):
    """A QRunnable worker to download a file in the background."""
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.signals = DownloadSignals()

    def run(self):
        try:
            # Validate URL scheme
            if not self.url.startswith("https://"):
                raise ValueError("Only HTTPS URLs are allowed for security.")

            response = requests.get(self.url, stream=True, timeout=(30, None))
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            # [SECURITY] Enforce maximum download size (10 GB)
            MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB
            if total_size > MAX_DOWNLOAD_SIZE:
                raise ValueError(f"File too large ({total_size / (1024**3):.1f} GB). Maximum allowed: 10 GB.")
            
            bytes_downloaded = 0

            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    # [SECURITY] Also check during download in case Content-Length was missing/wrong
                    if bytes_downloaded > MAX_DOWNLOAD_SIZE:
                        raise ValueError("Download exceeded maximum allowed size (10 GB).")
                    if total_size > 0:
                        progress_val = int((bytes_downloaded / total_size) * 100)
                        self.signals.progress.emit(progress_val)

            self.signals.finished.emit()

        except Exception as e:
            # Clean up partial download on error
            try:
                if os.path.exists(self.save_path):
                    os.remove(self.save_path)
            except OSError:
                pass
            self.signals.error.emit(str(e))