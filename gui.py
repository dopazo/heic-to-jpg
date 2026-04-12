"""Interfaz gráfica para el convertidor HEIC → JPG."""

from pathlib import Path

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from converter import ConversionWorker, count_files_in_folder, scan_folder

# ── Paleta de colores ──────────────────────────────────────────────
# Estética clara y cálida: fondo crema suave, acentos terracota
COLORS = {
    "bg": "#faf6f1",
    "surface": "#ffffff",
    "surface_hover": "#f0ebe4",
    "border": "#e0d5c7",
    "text": "#2c2417",
    "text_secondary": "#8a7d6b",
    "accent": "#c4693d",
    "accent_hover": "#d47a4e",
    "accent_glow": "rgba(196, 105, 61, 0.10)",
    "success": "#4a8c48",
    "error": "#c44040",
    "progress_bg": "#e8dfd4",
    "progress_fill": "#c4693d",
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["bg"]};
}}

QWidget#central {{
    background-color: {COLORS["bg"]};
}}

QLabel {{
    color: {COLORS["text"]};
    background: transparent;
}}

QLabel#title {{
    font-size: 26px;
    font-weight: 700;
    color: {COLORS["text"]};
    letter-spacing: 1px;
}}

QLabel#subtitle {{
    font-size: 13px;
    color: {COLORS["text_secondary"]};
    letter-spacing: 0.5px;
}}

QLabel#sectionLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {COLORS["text_secondary"]};
    letter-spacing: 1.5px;
    text-transform: uppercase;
}}

QLabel#folderPath {{
    font-size: 13px;
    color: {COLORS["text"]};
    padding: 12px 16px;
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
}}

QLabel#statsLabel {{
    font-size: 13px;
    color: {COLORS["text_secondary"]};
    padding: 4px 0;
}}

QLabel#heicCount {{
    font-size: 36px;
    font-weight: 700;
    color: {COLORS["accent"]};
}}

QLabel#heicUnit {{
    font-size: 13px;
    color: {COLORS["text_secondary"]};
    letter-spacing: 0.5px;
}}

QLabel#statusLabel {{
    font-size: 13px;
    color: {COLORS["text_secondary"]};
    padding: 4px 0;
}}

QPushButton#folderBtn {{
    font-size: 13px;
    font-weight: 600;
    color: {COLORS["text"]};
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 10px 20px;
    min-width: 160px;
}}

QPushButton#folderBtn:hover {{
    background-color: {COLORS["surface_hover"]};
    border-color: {COLORS["accent"]};
}}

QPushButton#convertBtn {{
    font-size: 15px;
    font-weight: 700;
    color: {COLORS["bg"]};
    background-color: {COLORS["accent"]};
    border: none;
    border-radius: 10px;
    padding: 14px 40px;
    letter-spacing: 0.5px;
}}

QPushButton#convertBtn:hover {{
    background-color: {COLORS["accent_hover"]};
}}

QPushButton#convertBtn:disabled {{
    background-color: {COLORS["border"]};
    color: {COLORS["text_secondary"]};
}}

QProgressBar {{
    background-color: {COLORS["progress_bg"]};
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    font-size: 0px;
}}

QProgressBar::chunk {{
    background-color: {COLORS["progress_fill"]};
    border-radius: 6px;
}}

QFrame#divider {{
    background-color: {COLORS["border"]};
    max-height: 1px;
}}

QFrame#statsCard {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 16px;
}}
"""


def _divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("sectionLabel")
    return lbl


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Convertidor HEIC → JPG")
        self.setMinimumSize(560, 680)
        self.resize(560, 720)

        self.input_folder: Path | None = None
        self.output_folder: Path | None = None
        self.worker: ConversionWorker | None = None

        self._build_ui()
        self.setStyleSheet(STYLESHEET)

    # ── Construcción de la interfaz ────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(36, 32, 36, 32)
        root.setSpacing(0)

        # ── Encabezado ──
        title = QLabel("Convertidor HEIC")
        title.setObjectName("title")
        root.addWidget(title)

        subtitle = QLabel("Convierte tus fotos de iPhone a formato JPG universal")
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)
        root.addSpacing(28)

        # ── Carpeta de entrada ──
        root.addWidget(_section_label("Carpeta de entrada"))
        root.addSpacing(8)

        input_row = QHBoxLayout()
        input_row.setSpacing(12)

        self.input_path_label = QLabel("Ninguna carpeta seleccionada")
        self.input_path_label.setObjectName("folderPath")
        self.input_path_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.input_path_label.setWordWrap(True)
        input_row.addWidget(self.input_path_label)

        input_btn = QPushButton("Seleccionar…")
        input_btn.setObjectName("folderBtn")
        input_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        input_btn.clicked.connect(self._select_input)
        input_row.addWidget(input_btn, alignment=Qt.AlignmentFlag.AlignTop)

        root.addLayout(input_row)

        self.input_stats = QLabel("")
        self.input_stats.setObjectName("statsLabel")
        self.input_stats.setVisible(False)
        root.addWidget(self.input_stats)

        root.addSpacing(20)

        # ── Carpeta de salida ──
        root.addWidget(_section_label("Carpeta de salida"))
        root.addSpacing(8)

        output_row = QHBoxLayout()
        output_row.setSpacing(12)

        self.output_path_label = QLabel("Ninguna carpeta seleccionada")
        self.output_path_label.setObjectName("folderPath")
        self.output_path_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.output_path_label.setWordWrap(True)
        output_row.addWidget(self.output_path_label)

        output_btn = QPushButton("Seleccionar…")
        output_btn.setObjectName("folderBtn")
        output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        output_btn.clicked.connect(self._select_output)
        output_row.addWidget(output_btn, alignment=Qt.AlignmentFlag.AlignTop)

        root.addLayout(output_row)

        self.output_stats = QLabel("")
        self.output_stats.setObjectName("statsLabel")
        self.output_stats.setVisible(False)
        root.addWidget(self.output_stats)

        root.addSpacing(24)
        root.addWidget(_divider())
        root.addSpacing(24)

        # ── Tarjeta de resumen ──
        stats_card = QFrame()
        stats_card.setObjectName("statsCard")
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setContentsMargins(20, 16, 20, 16)
        stats_layout.setSpacing(4)

        self.heic_count_label = QLabel("—")
        self.heic_count_label.setObjectName("heicCount")
        self.heic_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(self.heic_count_label)

        heic_unit = QLabel("imágenes HEIC para convertir")
        heic_unit.setObjectName("heicUnit")
        heic_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(heic_unit)

        root.addWidget(stats_card)
        root.addSpacing(24)

        # ── Barra de progreso ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.status_label)

        root.addSpacing(16)

        # ── Botón convertir ──
        self.convert_btn = QPushButton("Convertir")
        self.convert_btn.setObjectName("convertBtn")
        self.convert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self._start_conversion)
        root.addWidget(self.convert_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addStretch()

    # ── Selección de carpetas ──────────────────────────────────────
    def _select_input(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de entrada"
        )
        if not folder:
            return

        self.input_folder = Path(folder)
        self.input_path_label.setText(str(self.input_folder))

        scan = scan_folder(self.input_folder)
        self.input_stats.setText(
            f"{scan['total']} archivos encontrados  ·  "
            f"{scan['heic_count']} HEIC  ·  {scan['other_count']} otros"
        )
        self.input_stats.setVisible(True)

        self.heic_count_label.setText(str(scan["heic_count"]))
        self._update_convert_btn()

    def _select_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de salida"
        )
        if not folder:
            return

        self.output_folder = Path(folder)
        self.output_path_label.setText(str(self.output_folder))

        count = count_files_in_folder(self.output_folder)
        self.output_stats.setText(f"{count} archivos existentes en la carpeta")
        self.output_stats.setVisible(True)
        self._update_convert_btn()

    def _update_convert_btn(self):
        ready = self.input_folder is not None and self.output_folder is not None
        self.convert_btn.setEnabled(ready)

    # ── Conversión ─────────────────────────────────────────────────
    def _start_conversion(self):
        if not self.input_folder or not self.output_folder:
            return

        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("Convirtiendo…")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Preparando…")

        self.worker = ConversionWorker(self.input_folder, self.output_folder)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, percent: int, message: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def _on_finished(self, converted: int, copied: int):
        self.progress_bar.setValue(100)
        self.status_label.setText(
            f"¡Listo! {converted} imágenes convertidas, {copied} archivos copiados"
        )
        self.status_label.setStyleSheet(f"color: {COLORS['success']};")
        self.convert_btn.setText("Convertir")
        self.convert_btn.setEnabled(True)

        # Actualizar estadísticas de carpeta de salida
        if self.output_folder:
            count = count_files_in_folder(self.output_folder)
            self.output_stats.setText(f"{count} archivos existentes en la carpeta")

    def _on_error(self, message: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet(f"color: {COLORS['error']};")
        self.convert_btn.setText("Convertir")
        self.convert_btn.setEnabled(True)
