import logging
import pytube
import PyQt6.QtNetwork

from typing import Optional
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox, QPushButton
from app_settings import FORMAT, LOGGING_LEVEL
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl

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
        stream = video.streams.filter(only_audio=True).get_audio_only()
        stream.download("downloaded_music")

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(
            QUrl.fromLocalFile(f"./downloaded_music/{video.title}.mp4")
        )
        self.player.play()
