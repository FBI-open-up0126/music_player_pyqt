import sys
import logging
import gc

LOGGING_LEVEL = logging.DEBUG
FORMAT = "module %(name)s(%(levelname)s): %(message)s"

from PyQt6.QtWidgets import QApplication
import app


def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


def main():
    gc.set_debug(gc.DEBUG_UNCOLLECTABLE)

    application = QApplication(sys.argv)
    widget = app.App()
    widget.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    sys._excepthook = sys.excepthook
    sys.excepthook = exception_hook

    main()
