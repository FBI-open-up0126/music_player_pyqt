import logging
import json
import os
import coloredlogs
import tasks
import PyQt6.QtNetwork
import enum
import random

from typing import Iterable, Optional
from PyQt6 import QtGui
from PyQt6.QtCore import QPoint, QThread, QUrl, Qt, pyqtSlot
from PyQt6.QtGui import QAction, QBrush, QColor, QDropEvent, QPixmap, QResizeEvent, qRgb
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from app_settings import (
    CURRENT_PLAYING_SONG_COLOR,
    DOWNLOAD_AUDIO_TO,
    DOWNLOADS_DIRECTORY,
    FORMAT,
    LOGGING_LEVEL,
    PLAYLIST_DIRECTORY,
    THUMBNAIL_FOLDER,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6 import QtCore
from ui.add_playlist_ui import Ui_AddPlaylist
from ui.music_setting import Ui_MusicSetting
from PyQt6.QtWidgets import QProxyStyle, QStyle, QStyleOption, QStyleHintReturn

coloredlogs.install(fmt=FORMAT, level=LOGGING_LEVEL)
logger = logging.getLogger(__name__)

PlaylistType = list[dict[str, str]]


class QSliderDirectJumpStyle(QProxyStyle):
    def styleHint(
        self,
        hint: QStyle.StyleHint,
        option: QStyleOption = None,
        widget: QWidget = None,
        returnData: QStyleHintReturn = None,
    ) -> int:
        if hint == QStyle.StyleHint.SH_Slider_AbsoluteSetButtons:
            return (
                Qt.MouseButton.LeftButton
                | Qt.MouseButton.MiddleButton
                | Qt.MouseButton.RightButton
            ).value
        return super().styleHint(hint, option, widget, returnData)


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


class PlaybackMode(enum.Enum):
    Loop = 0
    LoopOnce = 1
    Sequential = 2
    Random = 3


class Playlist(QTableWidget):
    urls = dict()
    images = list()
    has_music = QtCore.pyqtSignal(int)

    playback_mode = PlaybackMode.Loop

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

        self.referencing_url = Playlist.urls
        self.referencing_images = Playlist.images

        self.is_downloads_playlist = True

        self.playlist_loading_thread = QThread()
        self.playlist_loader = tasks.PlaylistLoader(self)

        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.3)

        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)

        self.current_playing_index = -1

        self.cellClicked.connect(self.change_music)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_custom_context_menu)

        self.media_player.sourceChanged.connect(self.music_changed)
        self.media_player.errorOccurred.connect(self.handle_error)

        self.media_player.mediaStatusChanged.connect(self.media_status_changed)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

        self.download_musics_dialog = QDialog()
        self.download_musics_dialog.setWindowTitle("Add From Playlist")

        self.download_musics_listwidget = QListWidget(self.download_musics_dialog)
        self.download_musics_listwidget.setWindowTitle("Add From Downloads")

        palette = self.download_musics_listwidget.palette()
        self.download_musics_listwidget.setStyleSheet(
            f"QListWidget::item {{ border-bottom: 1px solid {palette.midlight().color().name()}; }} \
            QListWidget::item:selected {{ background-color: {palette.highlight().color().name()}; color: {palette.highlightedText().color().name()}; }}"
        )

        self.vertical_layout = QVBoxLayout(self.download_musics_dialog)
        self.vertical_layout.addWidget(self.download_musics_listwidget)

        self.buttons_layout = QHBoxLayout()
        self.vertical_layout.addLayout(self.buttons_layout)

        self.confirm_add_button = QPushButton("OK", self.download_musics_listwidget)
        self.buttons_layout.addWidget(self.confirm_add_button)

        self.cancel_button = QPushButton("Cancel", self.download_musics_listwidget)
        self.buttons_layout.addWidget(self.cancel_button)

        self.confirm_add_button.clicked.connect(self.add_music)
        self.cancel_button.clicked.connect(self.download_musics_dialog.hide)

        self.music_setting_dialog = QDialog()
        self.music_setting_ui = Ui_MusicSetting()
        self.music_setting_ui.setupUi(self.music_setting_dialog)

        self.music_setting_ui.browse_button.clicked.connect(self.browse_file)
        self.music_setting_ui.current_multiplier.setPageStep(50)
        self.music_setting_ui.current_multiplier.setSingleStep(25)
        self.music_setting_ui.current_multiplier.valueChanged.connect(
            lambda value: self.music_setting_ui.current_multiplier_label.setText(
                str(value / 100)
            )
        )

        self.music_setting_ui.ok_button.clicked.connect(self.save_music_setting)
        self.music_setting_ui.cancel_button.clicked.connect(
            self.music_setting_dialog.hide
        )
        self.music_setting_dialog.reject = self.save_music_setting

    def save_music_setting(self):
        music_setting = self.music_setting_ui

        self.set_data(music_setting.title.text(), "title", self.currentRow())
        self.item(self.currentRow(), 1).setText(music_setting.title.text())

        self.set_data(music_setting.author.text(), "author", self.currentRow())
        self.item(self.currentRow(), 2).setText(music_setting.title.text())

        self.set_data(
            music_setting.current_multiplier.value() / 100,
            "volume_multiplier",
            self.currentRow(),
        )
        self.music_setting_dialog.hide()

        if self.currentRow() == self.current_playing_index:
            self.music_changed()

    def browse_file(self):
        filename = QFileDialog.getOpenFileName(
            self.music_setting_dialog,
            "Select Image...",
            "",
            "Image Files (*.png *.jpg *.bmp *.jpeg *.ppm *.xbm *.xpm)",
        )[0]

    def set_downloads_playlist_mode(self):
        """
        set "self.is_downloads_playlist" to true and enable its feature

        it should be called right after the __init__ method of this class
        """
        self.is_downloads_playlist = True

        self.referencing_images = Playlist.images
        self.referencing_url = Playlist.urls

        self.setRowCount(0)

        if "musics" not in self.urls:
            self.urls["musics"] = list()

        for index, music_data in enumerate(self.urls["musics"]):
            try:
                title = music_data["title"]
                author = music_data["author"]
            except Exception as error:
                logger.error("Error Occurred: %s", error)
                continue
            self.push_item(self.images[index], title, author)

    @pyqtSlot(bytes, str, str)
    def push_item(self, data: bytes, title: str, author: str):
        self.insertRow(self.rowCount())
        image = QPixmap()
        image.loadFromData(data)
        image_label = QLabel()
        image_label.setPixmap(image)
        self.setCellWidget(self.rowCount() - 1, 0, image_label)
        self.setItem(self.rowCount() - 1, 1, QTableWidgetItem(title))
        self.setItem(self.rowCount() - 1, 2, QTableWidgetItem(author))
        self.resizeEvent(QResizeEvent(self.size(), self.size()))

    def load_music(self):
        self.playlist_loading_thread = QThread()
        self.playlist_loader = tasks.PlaylistLoader(self)

        self.playlist_loader.moveToThread(self.playlist_loading_thread)
        self.playlist_loader.done_loading.connect(self.playlist_loading_thread.quit)
        self.playlist_loader.item_loaded.connect(self.push_item)

        self.playlist_loading_thread.started.connect(self.playlist_loader.load)
        self.playlist_loading_thread.start()

    def load_from_playlist(self, playlist_name: str):
        path_dir = PLAYLIST_DIRECTORY + playlist_name + ".json"

        if not os.path.exists(path_dir):
            return

        self.current_playlist_name = playlist_name
        self.is_downloads_playlist = False

        self.referencing_images = list()
        self.referencing_url = dict()
        self.referencing_url["musics"] = list()

        with open(path_dir, mode="r") as file:
            data = json.loads(file.read())

        self.setRowCount(0)

        for music_data in data["musics"]:
            try:
                index = music_data["index"]
                image = self.images[index]
                url = self.urls["musics"][index]["id"]
                title = music_data.get("title", self.urls["musics"][index]["title"])
                author = music_data.get("author", self.urls["musics"][index]["author"])
                volume_multiplier = music_data.get(
                    "volume_multiplier", self.urls.get("volume_multiplier", 1.0)
                )

                self.referencing_url["musics"].append(
                    {
                        "id": url,
                        "index": index,
                        "title": title,
                        "author": author,
                        "volume_multiplier": volume_multiplier,
                    }
                )
                self.referencing_images.append(image)
            except Exception as error:
                logger.error("Error Occurred: %s", error)
                continue
            self.push_item(image, title, author)

        logger.debug(self.referencing_url)

    def save_current_playlist(self):
        if self.is_downloads_playlist:
            logger.debug("returned")
            return

        data = {"musics": []}

        for music in self.referencing_url["musics"]:
            data["musics"].append(
                {
                    "index": music["index"],
                    "title": music["title"],
                    "author": music["author"],
                }
            )

        logger.debug(data)
        with open(
            f"{PLAYLIST_DIRECTORY}{self.current_playlist_name}.json", mode="w"
        ) as file:
            file.write(json.dumps(data, indent=2))

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        for i in range(self.rowCount()):
            data = self.referencing_images[i]
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

    def get_data(self, data_name: str = "id", index: int = None, default_value=None):
        if index is None:
            index = self.current_playing_index

        try:
            return self.referencing_url["musics"][index][data_name]
        except Exception:
            return default_value

    def set_data(self, data, data_name: str = "id", index: int = None):
        self.referencing_url["musics"][index][data_name] = data

    def change_music(self):
        if self.current_playing_index == self.currentRow():
            self.music_changed()
            return

        self.current_playing_index = self.currentRow()

        self.media_player.setSource(
            QUrl.fromLocalFile(DOWNLOADS_DIRECTORY + self.get_data())
        )

    def pause(self):
        self.media_player.pause()

    def resume(self):
        self.media_player.play()

    def delete_playlist(self, delete_row: int):
        if self.rowCount() <= 0:
            return

        text = self.item(delete_row, 1).text()
        url = self.get_data(index=delete_row)

        self.removeRow(delete_row)

        self.media_player.setSource(QUrl())

        if self.is_downloads_playlist:
            try:
                os.remove(DOWNLOADS_DIRECTORY + url)
            except Exception as error:
                QMessageBox.warning(
                    self.top_widget,
                    "Failed to remove audio!".title(),
                    f"Failed to remove audio! Error: {error}",
                )

            try:
                os.remove(THUMBNAIL_FOLDER + url)
            except Exception as error:
                QMessageBox.warning(
                    self.top_widget,
                    "Failed to remove thumbnail".title(),
                    f"Failed to remove thumbnail! Error: {error}",
                )

        del self.referencing_url["musics"][delete_row]
        del self.referencing_images[delete_row]

        self.save_current_playlist()

        QMessageBox.information(
            self.top_widget,
            "Removed Successful!",
            f'Removed "{text}" from the playlist!',
        )

    def show_add_widget(self):
        self.download_musics_listwidget.clear()

        for music in self.urls["musics"]:
            self.download_musics_listwidget.addItem(music["title"])
            self.download_musics_listwidget.setMinimumWidth(
                self.download_musics_listwidget.sizeHintForColumn(0)
            )

        # self.download_musics_listwidget.setCurrentRow(-1)

        self.download_musics_dialog.show()
        self.download_musics_listwidget.selectionModel().clear()

    def show_custom_context_menu(self, pos: QPoint):
        menu = QMenu(self)

        if not self.is_downloads_playlist:
            add_music_from_downloads_playlist = QAction(
                "Add from downloads playlist", self
            )
            add_music_from_downloads_playlist.triggered.connect(self.show_add_widget)
            menu.addAction(add_music_from_downloads_playlist)

        delete_music_action = QAction("Delete", self)
        delete_music_action.triggered.connect(
            lambda: self.delete_playlist(self.currentRow())
        )
        menu.addAction(delete_music_action)

        music_setting_action = QAction("Settings", self)
        music_setting_action.triggered.connect(
            lambda: (
                self.music_setting_ui.author.setText(
                    self.referencing_url["musics"][self.currentRow()]["author"]
                ),
                self.music_setting_ui.title.setText(
                    self.referencing_url["musics"][self.currentRow()]["title"]
                ),
                self.music_setting_ui.current_multiplier.setRange(
                    0, int(1 / (self.top_widget.ui.volume_bar.value() / 100) * 100)
                ),
                self.music_setting_ui.current_multiplier.setValue(
                    int(
                        self.referencing_url["musics"][self.currentRow()][
                            "volume_multiplier"
                        ]
                        * 100
                    ),
                ),
                self.music_setting_ui.current_multiplier_label.setText(
                    str(
                        self.referencing_url["musics"][self.currentRow()][
                            "volume_multiplier"
                        ]
                    )
                ),
                self.music_setting_dialog.exec(),
            )
        )
        menu.addAction(music_setting_action)

        menu.exec(self.mapToGlobal(pos))

    def forward(self, start_over: bool = True) -> bool:
        """[start the next song]

        Args:
                start_over (bool, optional): [if start over after reaches to the end]. Defaults to True.

        Returns:
                bool: [returns true if the next song is none, and the start over is set to false]
        """
        index = self.current_playing_index + 1

        if index >= len(self.referencing_url["musics"]):
            if start_over:
                index = 0
            else:
                return True

        self.current_playing_index = index
        self.selectRow(self.current_playing_index)
        self.media_player.setSource(
            QUrl.fromLocalFile(DOWNLOADS_DIRECTORY + self.get_data())
        )
        return False

    def backward(self):
        index = self.current_playing_index - 1

        if index < 0:
            index = len(self.referencing_url["musics"]) - 1

        self.current_playing_index = index
        self.selectRow(self.current_playing_index)
        self.media_player.setSource(
            QUrl.fromLocalFile(DOWNLOADS_DIRECTORY + self.get_data())
        )

    def music_changed(self):
        is_playing = (
            self.media_player.playbackState() is QMediaPlayer.PlaybackState.PlayingState
        ) or self.top_widget.ui.resume_button.isVisible()

        volume_multiplier = self.referencing_url["musics"][self.current_playing_index][
            "volume_multiplier"
        ]

        new_volume = tasks.Settings.volume / 100 * volume_multiplier
        if new_volume > 1.0:
            new_volume = 1.0
        self.audio_output.setVolume(new_volume)

        if is_playing:
            self.media_player.play()

        for row in range(self.rowCount()):
            item = self.item(row, 1)
            if item.foreground() == QBrush(CURRENT_PLAYING_SONG_COLOR):
                item.setForeground(QColor(0, 0, 0))
                break

        if self.item(self.current_playing_index, 1) is not None:
            self.item(self.current_playing_index, 1).setForeground(
                CURRENT_PLAYING_SONG_COLOR
            )

        self.has_music.emit(self.current_playing_index)

    def handle_error(self, error):
        if error is QMediaPlayer.Error.ResourceError:
            # This is a bit stupid. The reason why I'm doing this is because if user drag the slider too fast
            # even if the resource exist this will still be called so when this happens I need to actually
            # check if the resource is valid or not other wise just keeps trying to play so user won't be confused
            if os.path.exists(DOWNLOAD_AUDIO_TO + f"/{self.get_data()}"):
                self.media_player.play()
                return

            QMessageBox.warning(
                self.top_widget,
                "Warning!",
                f"""Song "{self.item(self.current_playing_index, 1).text()}" \
does not exist! Check if you accidentally removed it""",
            )
            return

        logger.error("Error occurred: %s", error)
        self.media_player.play()

    def generate_random_playlist(self):
        self.random_playlist = list()
        for index, url in enumerate(self.referencing_url["musics"]):
            self.random_playlist.append((index, url["id"]))

        random.shuffle(self.random_playlist)

    def media_status_changed(self, status: QMediaPlayer.MediaStatus):
        if status is not QMediaPlayer.MediaStatus.EndOfMedia:
            return

        match self.playback_mode:
            case PlaybackMode.Loop:
                self.forward()
            case PlaybackMode.LoopOnce:
                self.media_player.play()
            case PlaybackMode.Sequential:
                self.forward(False)
            case PlaybackMode.Random:
                while True:
                    # when the user uses this the first time, the self.random_playlist might not generate, so catch the error and then genereate a new one and
                    # then start all over again
                    # might be a little stupid but idk lol
                    try:
                        self.current_playing_index = self.random_playlist[0][0]
                        self.media_player.setSource(
                            QUrl.fromLocalFile(
                                DOWNLOADS_DIRECTORY + self.random_playlist[0][1]
                            )
                        )
                        self.random_playlist.pop(0)
                        self.selectRow(self.current_playing_index)
                    except Exception:
                        self.generate_random_playlist()
                        continue
                    break

    @classmethod
    def set_playback_mode(cls, playback_mode: PlaybackMode):
        cls.playback_mode = playback_mode

    def dropEvent(self, event: QDropEvent):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on(event)

            rows = sorted(set(item.row() for item in self.selectedItems()))
            rows_to_move = [
                [
                    QTableWidgetItem(self.item(row_index, column_index))
                    for column_index in range(self.columnCount())
                ]
                for row_index in rows
            ]
            for row_index in reversed(rows):
                self.removeRow(row_index)
                if row_index < drop_row:
                    drop_row -= 1

            for row_index, data in enumerate(rows_to_move):
                row_index += drop_row
                self.insertRow(row_index)
                for column_index, column_data in enumerate(data):
                    self.setItem(row_index, column_index, column_data)
            event.accept()
            for row_index in range(len(rows_to_move)):
                self.item(drop_row + row_index, 0).setSelected(True)
                self.item(drop_row + row_index, 1).setSelected(True)
                self.item(drop_row + row_index, 2).setSelected(True)

        logger.debug(f"selected rows: {rows}, drop row:{drop_row}")

        (self.referencing_images[drop_row], self.referencing_images[rows[0]],) = (
            self.referencing_images[rows[0]],
            self.referencing_images[drop_row],
        )

        (
            self.referencing_url["musics"][drop_row],
            self.referencing_url["musics"][rows[0]],
        ) = (
            self.referencing_url["musics"][rows[0]],
            self.referencing_url["musics"][drop_row],
        )

        # a little hack to call the resize event for this widget so that the images can be loaded
        self.top_widget.resize(
            self.top_widget.width() + 1, self.top_widget.height() + 1
        )
        self.top_widget.resize(
            self.top_widget.width() - 1, self.top_widget.height() - 1
        )

        super().dropEvent(event)

    def drop_on(self, event: QDropEvent):
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            return self.rowCount()

        return (
            index.row() + 1
            if self.is_below(event.position().toPoint(), index)
            else index.row()
        )

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        # noinspection PyTypeChecker
        return (
            rect.contains(pos, True)
            and not (
                self.model().flags(index).value
                & QtCore.Qt.ItemFlag.ItemIsDropEnabled.value
            )
            and pos.y() >= rect.center().y()
        )

    def save_downloads_playlist(self):
        with open(PLAYLIST_DIRECTORY + "downloads.json", mode="w") as file:
            file.write(json.dumps({"musics": self.urls["musics"]}, indent=2))

    def add_music(self):
        current_index = self.download_musics_listwidget.currentRow()
        music = self.urls["musics"][current_index]

        self.referencing_url["musics"].append({**music, "index": current_index})
        self.referencing_images.append(self.images[current_index])
        self.push_item(self.images[current_index], music["title"], music["author"])

        QMessageBox.information(
            self.download_musics_dialog,
            "Added!",
            f"Added {self.urls['musics'][current_index]['title']} successfully to current playlist!",
        )

    def dataChanged(
        self,
        top_left: QtCore.QModelIndex,
        bottom_right: QtCore.QModelIndex,
        roles: Iterable[int] = None,
    ) -> None:
        if len(roles) == 0 or len(roles) == 1:
            return

        item = self.currentItem()
        column, row = self.currentIndex().column(), self.currentIndex().row()
        logger.debug(item.text())

        match column:
            case 1:
                self.referencing_url["musics"][row]["title"] = item.text()
            case 2:
                self.referencing_url["musics"][row]["author"] = item.text()


class PlaylistsHandler(QListWidget):
    playlists: list[str] = list()

    def __init__(self, parent: QWidget = None) -> None:
        from app import App

        super().__init__(parent)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.custom_context_menu)

        self.add_playlist_widget = QDialog()

        self.ui = Ui_AddPlaylist()
        self.ui.setupUi(self.add_playlist_widget)
        self.add_playlist_widget.hide()

        self.DEFAULT_TITLE = self.add_playlist_widget.windowTitle()

        self.load_playlists()

        self.ui.ok_button.clicked.connect(self.add_playlist)
        self.ui.cancel_button.clicked.connect(
            lambda: (self.add_playlist_widget.hide(), self.reset_widget())
        )

        self.itemClicked.connect(self.item_changed)

        self.top_widget = self.parent()
        while self.top_widget.parent() is not None:
            self.top_widget = self.top_widget.parent()
        self.top_widget: App = self.top_widget

    @staticmethod
    def generate_item(text: str) -> QListWidgetItem:
        item = QListWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def reset_widget(self):
        self.ui.playlist_name.clear()
        self.add_playlist_widget.setWindowTitle(self.DEFAULT_TITLE)

    def load_playlists(self):
        for filename in os.listdir(PLAYLIST_DIRECTORY):
            if filename == "downloads.json":
                continue

            if filename.endswith(".json"):
                filename = filename[: -len(".json")]

            self.playlists.append(filename)
            self.addItem(self.generate_item(filename))

    def add_playlist(self):
        self.addItem(self.generate_item(self.ui.playlist_name.text()))
        self.playlists.append(self.ui.playlist_name.text())

        with open(
            f"{PLAYLIST_DIRECTORY}{self.ui.playlist_name.text()}.json", mode="w"
        ) as file:
            file.write(json.dumps({"musics": []}, indent=2))

        self.add_playlist_widget.hide()
        self.reset_widget()

    def delete_playlist(self):
        from ui.playlist_ui import Ui_PlaylistWidget

        if self.currentRow() == -1:
            return

        item = self.currentItem()

        try:
            os.remove(f"{PLAYLIST_DIRECTORY}{item.text()}.json")
        except Exception as error:
            QMessageBox.warning(
                self,
                "Failed to delete playlist!",
                f'Failed to delete "{item.text()}"! Error: {error}',
            )
            return

        self.takeItem(self.row(item))

        ui_playlist: Ui_PlaylistWidget = self.top_widget.get_widget("playlist")
        ui_playlist.playlist.set_downloads_playlist_mode()

        self.deselect()

        QMessageBox.information(
            self, "Deleted Successful!", f"Deleted {item.text()} successfully!"
        )

    def edit_playlist(self):
        if self.currentItem() is None:
            return

        text = self.ui.playlist_name.text()
        old_name = self.currentItem().text()

        os.rename(
            PLAYLIST_DIRECTORY + old_name + ".json", PLAYLIST_DIRECTORY + text + ".json"
        )

        self.currentItem().setText(text)

        self.add_playlist_widget.hide()
        self.reset_widget()

    def custom_context_menu(self, pos: QPoint):
        menu = QMenu(self)

        add_action = QAction("Add Playlist", self)
        add_action.triggered.connect(
            lambda: (
                self.ui.ok_button.disconnect(),
                self.ui.ok_button.clicked.connect(self.add_playlist),
                self.add_playlist_widget.exec(),
            )
        )
        menu.addAction(add_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_playlist)
        menu.addAction(delete_action)

        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(
            lambda: (
                self.add_playlist_widget.setWindowTitle("Edit Playlist"),
                self.ui.playlist_name.setText(self.currentItem().text()),
                self.ui.ok_button.disconnect(),
                self.ui.ok_button.clicked.connect(self.edit_playlist),
                self.add_playlist_widget.exec(),
            )
        )
        menu.addAction(edit_action)

        menu.exec(self.mapToGlobal(pos))

    def item_changed(self, item: QListWidgetItem):
        for row in range(self.count()):
            current_item = self.item(row)
            if current_item.foreground().color() == QColor(115, 115, 115):
                current_item.setForeground(QColor(0, 0, 0))
                break

        item.setForeground(qRgb(115, 115, 115))

    def deselect(self):
        self.setCurrentRow(-1)
        for row in range(self.count()):
            item = self.item(row)
            if item.foreground().color() == QColor(115, 115, 115):
                item.setForeground(QColor(0, 0, 0))
