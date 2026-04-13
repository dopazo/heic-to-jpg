"""Interfaz gráfica para el convertidor HEIC → JPG."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontMetrics
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
    "border": "#c4b5a3",
    "text": "#2c2417",
    "text_secondary": "#6b5d4d",
    "accent": "#b85a2e",
    "accent_hover": "#c96a3e",
    "success": "#3d8b3d",
    "error": "#c44040",
    "progress_bg": "#e0d5c7",
    "progress_fill": "#b85a2e",
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
    font-size: 24px;
    font-weight: 700;
    color: {COLORS["text"]};
}}

QLabel#subtitle {{
    font-size: 13px;
    color: {COLORS["text_secondary"]};
}}

QLabel#sectionLabel {{
    font-size: 11px;
    font-weight: 700;
    color: {COLORS["text"]};
    letter-spacing: 1px;
}}

QLabel#folderPath {{
    font-size: 13px;
    color: {COLORS["text"]};
    padding: 10px 14px;
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
}}

QLabel#folderPathEmpty {{
    font-size: 13px;
    color: {COLORS["text_secondary"]};
    padding: 10px 14px;
    background-color: {COLORS["surface"]};
    border: 1px dashed {COLORS["border"]};
    border-radius: 6px;
    font-style: italic;
}}

QLabel#statsLabel {{
    font-size: 12px;
    color: {COLORS["text_secondary"]};
    padding: 2px 0;
}}

QLabel#heicCount {{
    font-size: 20px;
    font-weight: 700;
    color: {COLORS["accent"]};
}}

QLabel#heicUnit {{
    font-size: 13px;
    color: {COLORS["text"]};
}}

QLabel#statusLabel {{
    font-size: 13px;
    color: {COLORS["text_secondary"]};
    padding: 2px 0;
}}

QPushButton#folderBtn {{
    font-size: 13px;
    font-weight: 600;
    color: {COLORS["accent"]};
    background-color: {COLORS["surface"]};
    border: 2px solid {COLORS["accent"]};
    border-radius: 6px;
    padding: 10px 18px;
}}

QPushButton#folderBtn:hover {{
    background-color: {COLORS["accent"]};
    color: #ffffff;
}}

QPushButton#convertBtn {{
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    background-color: {COLORS["accent"]};
    border: none;
    border-radius: 8px;
    padding: 14px 52px;
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
    border-radius: 5px;
    height: 10px;
    text-align: center;
    font-size: 0px;
}}

QProgressBar::chunk {{
    background-color: {COLORS["progress_fill"]};
    border-radius: 5px;
}}

QFrame#divider {{
    background-color: {COLORS["border"]};
    max-height: 1px;
}}

QFrame#statsCard {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
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


def _elide_path(path: str, max_chars: int = 45) -> str:
    """Acorta un path largo mostrando …/últimas carpetas."""
    if len(path) <= max_chars:
        return path
    parts = Path(path).parts
    # Siempre mostrar drive + …/últimas partes
    result = path
    for i in range(1, len(parts)):
        candidate = str(Path(parts[0], "…", *parts[i:]))
        if len(candidate) <= max_chars:
            return candidate
    # Si aún es largo, mostrar solo las últimas 2 partes
    return str(Path("…", *parts[-2:]))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Convertidor HEIC → JPG")
        self.setMinimumSize(480, 490)
        self.resize(500, 490)

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
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(0)

        # ── Encabezado ──
        title = QLabel("Convertidor HEIC")
        title.setObjectName("title")
        root.addWidget(title)

        subtitle = QLabel("Convierte tus fotos de iPhone a formato JPG universal")
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)
        root.addSpacing(22)

        # ── Carpeta de entrada ──
        root.addWidget(_section_label("Carpeta de entrada"))
        root.addSpacing(6)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.input_path_label = QLabel("Ninguna carpeta seleccionada")
        self.input_path_label.setObjectName("folderPathEmpty")
        self.input_path_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
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

        root.addSpacing(16)

        # ── Carpeta de salida ──
        root.addWidget(_section_label("Carpeta de salida"))
        root.addSpacing(6)

        output_row = QHBoxLayout()
        output_row.setSpacing(10)

        self.output_path_label = QLabel("Ninguna carpeta seleccionada")
        self.output_path_label.setObjectName("folderPathEmpty")
        self.output_path_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
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

        root.addSpacing(18)
        root.addWidget(_divider())
        root.addSpacing(18)

        # ── Tarjeta de resumen (compacta, horizontal) ──
        stats_card = QFrame()
        stats_card.setObjectName("statsCard")
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(20, 14, 20, 14)
        stats_layout.setSpacing(10)

        self.heic_count_label = QLabel("—")
        self.heic_count_label.setObjectName("heicCount")
        stats_layout.addWidget(self.heic_count_label)

        heic_unit = QLabel("imágenes HEIC para convertir")
        heic_unit.setObjectName("heicUnit")
        stats_layout.addWidget(heic_unit)

        stats_layout.addStretch()

        root.addWidget(stats_card)
        root.addSpacing(18)

        # ── Barra de progreso ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.status_label)

        root.addSpacing(12)

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
        self.input_path_label.setText(_elide_path(str(self.input_folder)))
        self.input_path_label.setToolTip(str(self.input_folder))
        self.input_path_label.setObjectName("folderPath")
        self.input_path_label.setStyle(self.input_path_label.style())

        scan = scan_folder(self.input_folder)
        self.input_stats.setText(
            f"{scan['total']} archivos  ·  "
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
        self.output_path_label.setText(_elide_path(str(self.output_folder)))
        self.output_path_label.setToolTip(str(self.output_folder))
        self.output_path_label.setObjectName("folderPath")
        self.output_path_label.setStyle(self.output_path_label.style())

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
        self.status_label.setStyleSheet("")

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
            f"¡Listo! {converted} convertidas, {copied} copiados"
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
