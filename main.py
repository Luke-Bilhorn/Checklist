import sys

from PySide6.QtWidgets import QApplication

from checklist.main_window import MainWindow
from checklist.theme import global_qss


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(global_qss())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
