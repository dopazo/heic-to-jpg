"""Punto de entrada del Convertidor HEIC → JPG."""

import sys

from PyQt6.QtWidgets import QApplication

from gui import MainWindow


def main():
    app = QApplication(sys.argv)

    # Fuente base
    app.setFont(app.font())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
