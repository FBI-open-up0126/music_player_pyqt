import logging
import sys
import app
import os
import coloredlogs

os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"
try:
    os.makedirs("./thumbnails")
    os.makedirs("./playlists")
    if not os.path.exists(PLAYLIST_DIRECTORY + "downloads.json"):
        with open(PLAYLIST_DIRECTORY + "downloads.json", mode="w+") as file:
            file.write("{ musics: [] }")
except Exception:
    pass

from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget
from app_settings import (
    FORMAT,
    IMAGE_RESOURCES,
    LOGGING_LEVEL,
    PLAYLIST_DIRECTORY,
    CustomFormatter,
)
from PyQt6 import QtCore

coloredlogs.install(fmt=FORMAT, level=LOGGING_LEVEL)
logger = logging.getLogger(__name__)

QtCore.QDir.addSearchPath("images", "resources/images/")


def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


def check_resource(widget: QWidget):
    for path in IMAGE_RESOURCES:
        if not os.path.exists(path):
            QMessageBox.critical(
                widget,
                "Missing Resource",
                f'Missing "{path}"! Check if you accidentally delete something, and try to reinstall!',
            )
            sys.exit(1)


def main():
    # player = QMediaPlayer()
    # audio_output = QAudioOutput()
    # player.setAudioOutput(audio_output)
    # player.setSource(QUrl.fromLocalFile(f"./downloads/f2xGxd9xPYA"))
    # player.play()

    # logger.debug(json.dumps({1: 1}, indent=2))

    application = QApplication(sys.argv)
    widget = app.App()

    check_resource(widget)

    widget.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    sys._excepthook = sys.excepthook
    sys.excepthook = exception_hook

    main()
