import logging
import json
import os
import pytube

from typing import Optional
from PyQt6 import QtGui
from PyQt6.QtWidgets import (
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QWidget,
)
from app_settings import DOWNLOADS_PLAYLIST, FORMAT, LOGGING_LEVEL, PLAYLIST_DIRECTORY, YOUTUBE_PREFIX

logging.basicConfig(level=LOGGING_LEVEL, format=FORMAT)
logger = logging.getLogger(__name__)

PlaylistType = dict[str, dict[str, str]]


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


class MyLineEdit(QLineEdit):
    def __init__(self, parent: QWidget):
        super().__init__(parent)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.selectAll()


class MusicList(QTableWidget):
    urls: PlaylistType = dict()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.top_widget: QWidget = self.parent()
        while self.top_widget.parent() is not None:
            self.top_widget: QWidget = self.top_widget.parent()

        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

        self.is_downloads_playlist = False

    def set_downloads_playlist_mode(self):
        """
        set "self.is_downloads_playlist" to true and enable its feature
        """
        self.is_downloads_playlist = True

    def load_music(self, playlist_name: str = ""):
        playlist_name = PLAYLIST_DIRECTORY + playlist_name
        if self.is_downloads_playlist:
            playlist_name = DOWNLOADS_PLAYLIST

        if not os.path.isdir(playlist_name):
            match self.is_downloads_playlist:
                case True:
                    os.makedirs(DOWNLOADS_PLAYLIST)
                case False:
                    QMessageBox.warning(
                        self.top_widget,
                        "Playlist Does Not Exist",
                        "This playlist does not exist! Check if you accidentally delete it or what!",
                    )
                    
        match self.is_downloads_playlist:
            case True:
                for filename in os.listdir(playlist_name):
                    url = YOUTUBE_PREFIX + filename
                    try:
                        video = pytube.YouTube(url)
                        self.urls.update({
                            filename: {
                                "thumbnail_url": video.thumbnail_url,
                                "title": video.title,
                                "author": video.author
                            }
                        })
                        logger.debug(self.urls)
                    except Exception as error:
                        logger.error("Something went wrong! %s", error)
            case False:
                ...
        
            

    # def test(self):
    #     self.urls.update(
    #         {
    #             "a url": {
    #                 "thumbnail": "thumbnail url",
    #                 "title": "title",
    #                 "author": "author",
    #             }
    #         }
    #     )
    #     self.urls.update(
    #         {
    #             "another url": {
    #                 "thumbnail": "thumbnail url",
    #                 "title": "title",
    #                 "author": "author",
    #             }
    #         }
    #     )

    #     urls = json.dumps(self.urls, indent=2)
    #     logger.debug(urls)
