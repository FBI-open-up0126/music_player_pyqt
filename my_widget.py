import logging
import pytube

from typing import Optional
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox, QPushButton
from main import LOGGING_LEVEL, FORMAT

logging.basicConfig(level=LOGGING_LEVEL, format=FORMAT)
logger = logging.getLogger(__name__)


class DownloadButton(QPushButton):
    def __init__(self, link: Optional[str], parent: QtWidgets):
        super().__init__("Download")

        self.link = link
        self.parent = parent
        self.clicked.connect(self.download)

    def download(self):
        if self.link == None:
            QMessageBox.critical(
                self.parent,
                "Cannot Download!",
                "Cannot download this video! (Error: No Link)",
            )
            return

        video = pytube.YouTube(self.link)
        streams = video.streams.filter(only_audio=True).get_audio_only()
        streams.download("downloaded_music")
