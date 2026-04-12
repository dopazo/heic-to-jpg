"""Lógica de conversión HEIC → JPG y copia de archivos."""

import os
import shutil
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener
from PyQt6.QtCore import QThread, pyqtSignal

register_heif_opener()

HEIC_EXTENSIONS = {".heic", ".heif"}


def scan_folder(folder: Path) -> dict:
    """Escanea una carpeta recursivamente y clasifica los archivos."""
    heic_files: list[Path] = []
    other_files: list[Path] = []

    for root, _, files in os.walk(folder):
        for name in files:
            file_path = Path(root) / name
            if file_path.suffix.lower() in HEIC_EXTENSIONS:
                heic_files.append(file_path)
            else:
                other_files.append(file_path)

    return {
        "heic": heic_files,
        "other": other_files,
        "total": len(heic_files) + len(other_files),
        "heic_count": len(heic_files),
        "other_count": len(other_files),
    }


def count_files_in_folder(folder: Path) -> int:
    """Cuenta archivos en una carpeta recursivamente."""
    count = 0
    if folder.exists():
        for _, _, files in os.walk(folder):
            count += len(files)
    return count


def safe_output_path(dest: Path) -> Path:
    """Genera un nombre único si el archivo ya existe, usando sufijos _2, _3, etc."""
    if not dest.exists():
        return dest

    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 2

    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


class ConversionWorker(QThread):
    """Hilo de trabajo para la conversión de archivos."""

    progress = pyqtSignal(int, str)  # (porcentaje, mensaje)
    finished_ok = pyqtSignal(int, int)  # (convertidos, copiados)
    error = pyqtSignal(str)

    def __init__(self, input_folder: Path, output_folder: Path):
        super().__init__()
        self.input_folder = input_folder
        self.output_folder = output_folder

    def run(self):
        try:
            scan = scan_folder(self.input_folder)
            all_files = scan["heic"] + scan["other"]
            total = len(all_files)

            if total == 0:
                self.finished_ok.emit(0, 0)
                return

            converted = 0
            copied = 0

            for i, file_path in enumerate(all_files):
                rel_path = file_path.relative_to(self.input_folder)
                dest_dir = self.output_folder / rel_path.parent
                dest_dir.mkdir(parents=True, exist_ok=True)

                if file_path.suffix.lower() in HEIC_EXTENSIONS:
                    dest = dest_dir / (rel_path.stem + ".jpg")
                    dest = safe_output_path(dest)
                    self.progress.emit(
                        int((i / total) * 100),
                        f"Convirtiendo: {rel_path.name}",
                    )
                    img = Image.open(file_path)
                    img.save(dest, "JPEG", quality=95)
                    converted += 1
                else:
                    dest = dest_dir / rel_path.name
                    dest = safe_output_path(dest)
                    self.progress.emit(
                        int((i / total) * 100),
                        f"Copiando: {rel_path.name}",
                    )
                    shutil.copy2(file_path, dest)
                    copied += 1

            self.progress.emit(100, "¡Completado!")
            self.finished_ok.emit(converted, copied)

        except Exception as e:
            self.error.emit(str(e))
