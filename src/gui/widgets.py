# src/gui/widgets.py

import os
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QRadialGradient, QFontMetrics
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF

class DialProgressBar(QWidget):
    """A circular progress bar that paints its own status light and text."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self._value = 0
        self._status_text = "Ready"
        self._status_color = QColor("#2ecc71")
        self.reset()

    def setValue(self, value: int):
        self._value = max(0, min(value, 100))
        self.update()

    def setState(self, state: str):
        states = {
            'loading': ("Loading Model...", QColor("#f39c12")), # Amber color
            'ready': ("Ready", QColor("#2ecc71")),
            'analyzing': ("Analyzing...", QColor("#3498db")),
            'summarizing': ("Summarizing...", QColor("#9b59b6")),
            'paused': ("Paused", QColor("#f1c40f")),
            'stopped': ("Stopped", QColor("#e74c3c")),
        }
        text, color = states.get(state.lower(), ("Unknown", QColor("#bdc3c7")))
        self._status_text = text
        self._status_color = color
        self.update()

    def reset(self):
        self.setValue(0)
        self.setState('ready')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        rect = QRectF(
            (self.width() - side) / 2.0, (self.height() - side) / 2.0,
            side, side
        )
        drawing_rect = rect.adjusted(10, 10, -10, -10)
        start_angle, span_angle = 90 * 16, -int(self._value / 100 * 360 * 16)

        # Background and Progress Arcs
        pen = QPen(QColor("#3B4252"), 8, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawArc(drawing_rect, 0, 360 * 16)
        pen.setColor(self._status_color)
        painter.setPen(pen)
        painter.drawArc(drawing_rect, start_angle, span_angle)

        # --- Upper Segment: Percentage Text ---
        percent_font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        percent_font.setPixelSize(int(drawing_rect.height() * 0.35))
        painter.setFont(percent_font)
        painter.setPen(QColor("#ECEFF4"))
        percent_rect = drawing_rect.adjusted(0, 0, 0, -int(drawing_rect.height() * 0.2))
        painter.drawText(percent_rect, Qt.AlignmentFlag.AlignCenter, f"{self._value}%")

        # --- Lower Segment: Status Indicator and Text (Refined Layout) ---
        status_rect = drawing_rect.adjusted(0, int(drawing_rect.height() * 0.3), 0, 0)
        
        # Define fonts and sizes
        status_font = QFont("Segoe UI", 10, QFont.Weight.Normal)
        status_font.setPixelSize(int(drawing_rect.height() * 0.12))
        indicator_size = int(status_font.pixelSize() * 1.2) # Make indicator proportional to font
        
        # Calculate the total width of the indicator + text
        fm = QFontMetrics(status_font)
        text_width = fm.horizontalAdvance(self._status_text)
        spacing = 5
        total_content_width = indicator_size + spacing + text_width
        
        # Calculate the starting X position to center the whole content block
        start_x = status_rect.center().x() - (total_content_width / 2)
        
        # 1. Paint the glowing indicator light
        indicator_y = status_rect.center().y() - indicator_size / 2
        indicator_center = QPointF(start_x + indicator_size / 2, indicator_y + indicator_size / 2)
        
        gradient = QRadialGradient(indicator_center, indicator_size / 2)
        center_color = QColor(self._status_color)
        center_color.setHsv(center_color.hue(), int(center_color.saturationF() * 255 * 0.5), 255)
        gradient.setColorAt(0, center_color)
        gradient.setColorAt(0.5, self._status_color)
        transparent_color = QColor(self._status_color)
        transparent_color.setAlpha(0)
        gradient.setColorAt(1, transparent_color)
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(indicator_center, indicator_size / 2, indicator_size / 2)
        
        # 2. Paint the status text
        painter.setFont(status_font)
        painter.setPen(self._status_color)
        text_x = start_x + indicator_size + spacing
        text_y = status_rect.center().y() + fm.ascent() / 2 - fm.descent()
        painter.drawText(QPointF(text_x, text_y), self._status_text)

class DropArea(QLabel):
    """A custom QLabel widget that accepts drag-and-drop file events."""
    dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Drop documents here or")
        self.setObjectName("dropArea")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("border: 2px dashed #88C0D0;")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("border: 2px dashed #4C566A;")

    def dropEvent(self, event):
        SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.txt'}
        file_paths = [
            url.toLocalFile() for url in event.mimeData().urls()
            if os.path.splitext(url.toLocalFile())[1].lower() in SUPPORTED_EXTENSIONS
        ]
        if file_paths:
            self.dropped.emit(file_paths)
        self.setStyleSheet("border: 2px dashed #4C566A;")