import logging
import sys
import app

from PyQt6.QtWidgets import QApplication
from app_settings import FORMAT, LOGGING_LEVEL

logging.basicConfig(level=LOGGING_LEVEL, format=FORMAT)
logger = logging.getLogger(__name__)


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
