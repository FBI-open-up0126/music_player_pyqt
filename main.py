from PyQt6.QtWidgets import QApplication
import sys

from app import App


def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


def main():
    application = QApplication(sys.argv)
    widget = App()
    widget.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    sys._excepthook = sys.excepthook
    sys.excepthook = exception_hook

    main()
