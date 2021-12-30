import logging
import sys
import app
import os

os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"
try:
    os.makedirs("./thumbnails")
except Exception:
    pass

from PyQt6.QtWidgets import QApplication
from app_settings import FORMAT, LOGGING_LEVEL
from PyQt6 import QtCore

logging.basicConfig(level=LOGGING_LEVEL, format=FORMAT)
logger = logging.getLogger(__name__)

QtCore.QDir.addSearchPath("images", "resources/images/")


def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


def main():
    # player = QMediaPlayer()
    # audio_output = QAudioOutput()
    # player.setAudioOutput(audio_output)
    # player.setSource(QUrl.fromLocalFile(f"./downloads/f2xGxd9xPYA"))
    # player.play()

    application = QApplication(sys.argv)
    widget = app.App()
    widget.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    sys._excepthook = sys.excepthook
    sys.excepthook = exception_hook

    main()
