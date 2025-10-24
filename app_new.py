from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from src.ui.start_window import StartWindow


def main() -> int:
    app = QApplication(sys.argv)
    start_window = StartWindow()
    start_window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

