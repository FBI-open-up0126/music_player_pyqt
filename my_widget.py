from functools import partial
import logging
from PyQt6 import QtCore
import pytube
import PyQt6.QtNetwork

from typing import Optional
from PyQt6.QtWidgets import QMessageBox, QPushButton, QWidget
from app_settings import FORMAT, LOGGING_LEVEL
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QThread, QUrl

from tasks import DownloadVideo

logging.basicConfig(level=LOGGING_LEVEL, format=FORMAT)
logger = logging.getLogger(__name__)


class DownloadButton(QPushButton):
    done_downloading = QtCore.pyqtSignal()

    def __init__(self, link: Optional[str], parent: QWidget):
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

        self.setText("Downloading...")
        self.setEnabled(False)

        self.download_thread = QThread()
        self.download_video = DownloadVideo(self.link)

        self.download_video.moveToThread(self.download_thread)
        self.download_video.done.connect(self.download_thread.quit)
        self.download_video.done.connect(self.done_downloading.emit)
        self.download_video.done.connect(partial(self.setText, "Downloaded!"))
        self.download_video.done.connect(partial(self.setEnabled, True))

        self.download_thread.started.connect(self.download_video.start_download)
        self.download_thread.start()

        # self.player = QMediaPlayer()
        # self.audio_output = QAudioOutput()
        # self.player.setAudioOutput(self.audio_output)
        # self.player.setSource(
        #     QUrl.fromLocalFile(f"./downloaded_music/{video.title}.mp4")
        # )
        # self.player.play()
