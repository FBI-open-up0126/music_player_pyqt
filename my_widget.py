import logging

from typing import Optional
from PyQt6.QtWidgets import QPushButton, QWidget
from app_settings import FORMAT, LOGGING_LEVEL

logging.basicConfig(level=LOGGING_LEVEL, format=FORMAT)
logger = logging.getLogger(__name__)


class DownloadButton(QPushButton):
    def __init__(self, link: Optional[str], parent: QWidget):
        super().__init__("Download", parent)

        self.link = link

        # self.player = QMediaPlayer()
        # self.audio_output = QAudioOutput()
        # self.player.setAudioOutput(self.audio_output)
        # self.player.setSource(
        #     QUrl.fromLocalFile(f"./downloaded_music/{video.title}.mp4")
        # )
        # self.player.play()
