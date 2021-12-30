import logging
import json
import os
from PyQt6.sip import delete
import pytube
import urllib.request as urlreq
import tasks
import time
import PyQt6.QtNetwork

from typing import Optional
from PyQt6 import QtGui
from PyQt6.QtCore import QPoint, QThread, QUrl, Qt, pyqtSlot
from PyQt6.QtGui import QAction, QPixmap, QResizeEvent
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from app_settings import (
    DOWNLOADS_DIRECTORY,
    FORMAT,
    LOGGING_LEVEL,
)
from functools import partial
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6 import QtCore

logging.basicConfig(level=LOGGING_LEVEL, format=FORMAT)
logger = logging.getLogger(__name__)

PlaylistType = list[dict[str, str]]


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

    def mousePressEvent(self, _: QtGui.QMouseEvent) -> None:
        self.selectAll()


class Playlist(QTableWidget):
    # urls: PlaylistType = list()
    urls = list()
    images = list()
    has_music = QtCore.pyqtSignal(int)
    # done_loading = QtCore.pyqtSignal()
    # error_occurred = QtCore.pyqtSignal(Exception)

    def __init__(self, parent=None):
        from app import App

        super().__init__(parent)

        self.top_widget: QWidget = self.parent()
        while self.top_widget.parent() is not None:
            self.top_widget: QWidget = self.top_widget.parent()
        self.top_widget: App = self.top_widget

        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

        self.verticalScrollBar().setSingleStep(20)

        self.referenced_url = list()
        self.referenced_images = list()

        self.is_downloads_playlist = False

        self.playlist_loading_thread = QThread()
        self.playlist_loader = tasks.PlaylistLoader(self)

        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.3)

        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

        self.current_playing_index = 0

        self.cellClicked.connect(self.change_music)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_custom_context_menu)

        self.player.sourceChanged.connect(self.after_change)
        self.player.errorOccurred.connect(self.handle_error)

    def set_downloads_playlist_mode(self):
        """
        set "self.is_downloads_playlist" to true and enable its feature

        it should be called right after the __init__ method of this class
        """
        self.is_downloads_playlist = True
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)

        self.referenced_url = Playlist.urls
        self.referenced_images = Playlist.images

    @pyqtSlot(bytes, str, str)
    def push_item(self, data: bytes, title: str, author: str):
        self.referenced_images.append(data)
        self.insertRow(self.rowCount())
        image = QPixmap()
        image.loadFromData(data)
        image_label = QLabel()
        image_label.setPixmap(image)
        self.setCellWidget(self.rowCount() - 1, 0, image_label)
        self.setItem(self.rowCount() - 1, 1, QTableWidgetItem(title))
        self.setItem(self.rowCount() - 1, 2, QTableWidgetItem(author))
        self.resizeEvent(QResizeEvent(self.size(), self.size()))

    def load_music(self, playlist_name: str = ""):
        self.playlist_loading_thread = QThread()

        self.playlist_loader.moveToThread(self.playlist_loading_thread)
        self.playlist_loader.done_loading.connect(self.playlist_loading_thread.quit)
        self.playlist_loader.item_loaded.connect(self.push_item)

        self.playlist_loading_thread.started.connect(
            partial(self.playlist_loader.load, playlist_name)
        )
        self.playlist_loading_thread.start()

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        for i in range(self.rowCount()):
            data = self.referenced_images[i]
            image = QPixmap()
            image.loadFromData(data)

            height_to_width_ratio = image.height() / image.width()
            reduced_width = int(self.width() / 3)
            reduced_height = int(reduced_width * height_to_width_ratio)

            image = image.scaled(
                reduced_width,
                reduced_height,
                aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                transformMode=Qt.TransformationMode.SmoothTransformation,
            )
            label = QLabel()
            label.setPixmap(image)
            self.setCellWidget(i, 0, label)

        return super().resizeEvent(e)

    def change_music(self):
        self.current_playing_index = self.currentRow()

        self.player.setSource(
            QUrl.fromLocalFile(
                DOWNLOADS_DIRECTORY + self.referenced_url[self.current_playing_index]
            )
        )

    def pause(self):
        self.player.pause()

    def resume(self):
        self.player.play()

    def delete_playlist(self, delete_row: int):
        self.removeRow(delete_row)

    def show_custom_context_menu(self, pos: QPoint):
        menu = QMenu(self)

        if not self.is_downloads_playlist:
            add_music_from_downloads_playlist = QAction(
                "Add from downloads playlist", self
            )
            menu.addAction(add_music_from_downloads_playlist)

        delete_music_action = QAction("Delete", self)
        delete_music_action.triggered.connect(
            lambda: self.delete_playlist(self.currentRow())
        )
        menu.addAction(delete_music_action)

        menu.exec(self.mapToGlobal(pos))

    def forward(self, start_over: bool = True) -> bool:
        """[start the next song]

        Args:
            start_over (bool, optional): [if start over after reaches to the end]. Defaults to True.

        Returns:
            bool: [returns true if the next song is none, and the start over is set to false]
        """
        index = self.current_playing_index + 1

        if index >= len(self.referenced_url):
            if start_over:
                index = 0
            else:
                return True

        self.current_playing_index = index
        self.selectRow(self.current_playing_index)
        self.player.setSource(
            QUrl.fromLocalFile(DOWNLOADS_DIRECTORY + self.referenced_url[index])
        )
        return False

    def backward(self):
        index = self.current_playing_index - 1

        if index < 0:
            index = len(self.referenced_url) - 1

        self.current_playing_index = index
        self.selectRow(self.current_playing_index)
        self.player.setSource(
            QUrl.fromLocalFile(DOWNLOADS_DIRECTORY + self.referenced_url[index])
        )

    def after_change(self):
        is_playing = (
            self.player.playbackState is QMediaPlayer.PlaybackState.PlayingState
        ) or self.top_widget.ui.resume_button.isVisible()

        if is_playing:
            self.player.play()

        self.has_music.emit(self.current_playing_index)

    def handle_error(self, *_):
        self.player.play()
