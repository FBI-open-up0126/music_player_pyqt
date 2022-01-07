import time
import datetime
import logging
import coloredlogs
import pytube
import tasks

from PyQt6.QtCore import QDateTime, QThread, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from functools import partial
from ui.app import Ui_App
from ui.help_dialog import Ui_HelpDialog
from ui.search_menu import Ui_SearchMenu
from ui.welcome_menu import Ui_WelcomeMenu
from ui.download_from_url_dialog import Ui_DownloadFromURL
from my_widget import DownloadButton, PlaybackMode
from PyQt6 import QtGui
from app_settings import FORMAT, LOGGING_LEVEL
from ui.playlist_ui import Ui_PlaylistWidget
from tasks import Settings

coloredlogs.install(fmt=FORMAT, level=LOGGING_LEVEL)
logger = logging.getLogger(__name__)


class App(QWidget):
    download_threads: dict[str, tuple[QThread, tasks.VideoDownloadManager]] = {}
    video_download_manager = tasks.VideoDownloadManager()

    def __init__(self, parent=None):
        super().__init__(parent)

        # initialize variables
        self.ui = Ui_App()
        self.ui.setupUi(self)

        Settings.read_settings()

        self.ui.pause_button.setIcon(QtGui.QIcon("images:pause.png"))
        self.ui.pause_button.setEnabled(False)
        self.ui.resume_button.setIcon(QtGui.QIcon("images:resume.png"))
        self.ui.resume_button.hide()

        self.ui.backward_button.setIcon(QtGui.QIcon("images:backward.png"))
        self.ui.backward_button.setEnabled(False)

        self.ui.forward_button.setIcon(QtGui.QIcon("images:forward.png"))
        self.ui.forward_button.setEnabled(False)

        self.ui.playbackmode_loop.setIcon(QtGui.QIcon("images:loop.png"))
        self.ui.playbackmode_looponce.setIcon(QtGui.QIcon("images:repeat.png"))
        self.ui.playbackmode_random.setIcon(QtGui.QIcon("images:random.png"))
        self.ui.playbackmode_sequential.setIcon(QtGui.QIcon("images:sequential.png"))

        self.ui.playbackmode_loop.hide()
        self.ui.playbackmode_looponce.hide()
        self.ui.playbackmode_random.hide()
        self.ui.playbackmode_sequential.hide()

        match Settings.playback_mode:
            case PlaybackMode.Loop:
                self.ui.playbackmode_loop.show()
            case PlaybackMode.LoopOnce:
                self.ui.playbackmode_looponce.show()
            case PlaybackMode.Sequential:
                self.ui.playbackmode_sequential.show()
            case PlaybackMode.Random:
                self.ui.playbackmode_random.show()

        self.ui_help_dialog = Ui_HelpDialog()
        self.help_dialog = QDialog()

        self.ui_help_dialog.setupUi(self.help_dialog)
        self.ui_help_dialog.text_browser.setOpenExternalLinks(True)

        self.ui_download_directly = Ui_DownloadFromURL()
        self.download_directly_dialog = QDialog()
        self.ui_download_directly.setupUi(self.download_directly_dialog)

        self.resize(1600, 1000)

        self.mainmenu_widgets: dict[str, tuple[QWidget, object]] = {}

        self.vertical_layout = QVBoxLayout(self.ui.main_menu)
        self.vertical_layout.setSpacing(0)
        self.vertical_layout.setContentsMargins(0, 0, 0, 0)

        self.search_video = tasks.SearchVideo()
        self.image_loader = tasks.ImageLoader()

        self.image_loading_thread = QThread()
        self.search_thread = QThread()

        self.image_loading_thread.setTerminationEnabled(True)
        self.search_thread.setTerminationEnabled(True)

        App.video_download_manager.done_downloading.connect(self.done_downloading)

        # initialize widgets
        ui_welcome_menu: Ui_WelcomeMenu = self.add_widget(
            Ui_WelcomeMenu(), "welcome_menu"
        )
        now = datetime.datetime.now()
        if now.hour in range(5, 12):
            ui_welcome_menu.greetings.setText("Good Morning")
        elif now.hour in range(12, 18):
            ui_welcome_menu.greetings.setText("Good Afternoon")
        else:
            ui_welcome_menu.greetings.setText("Good Evening")

        ui_search_menu: Ui_SearchMenu = self.add_widget(Ui_SearchMenu(), "search_menu")
        ui_search_menu.results.hide()
        ui_search_menu.results.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        ui_search_menu.results.setVerticalScrollMode(
            QTableWidget.ScrollMode.ScrollPerPixel
        )
        ui_search_menu.results.setHorizontalScrollMode(
            QTableWidget.ScrollMode.ScrollPerPixel
        )
        ui_search_menu.results.horizontalHeader().setStretchLastSection(True)
        ui_search_menu.results.verticalScrollBar().setSingleStep(20)

        ui_playlist: Ui_PlaylistWidget = self.add_widget(
            Ui_PlaylistWidget(), "playlist"
        )
        # ui_playlist.playlist.set_downloads_playlist_mode()
        ui_playlist.playlist.load_music()
        ui_playlist.playlist.set_playback_mode(Settings.playback_mode)

        self.get_widget("welcome_menu", 0).show()

        # initialize connections
        self.ui.search_button.clicked.connect(self.start_search)
        self.ui.search_bar.returnPressed.connect(self.start_search)
        ui_welcome_menu.help_button.clicked.connect(self.help_dialog.exec)
        self.ui.download_from_url_button.clicked.connect(
            self.download_directly_dialog.exec
        )
        self.ui_download_directly.download_button.clicked.connect(
            lambda: self.download_directly_from_url(
                self.ui_download_directly.url_edit.text(),
                self.ui_download_directly.download_button,
            )
        )
        self.ui.download_from_url_button.clicked.connect(
            lambda: (
                self.ui_download_directly.download_button.setEnabled(True),
                self.ui_download_directly.url_edit.clear(),
            )
        )
        self.ui_download_directly.cancel_button.clicked.connect(
            self.download_directly_dialog.hide
        )
        self.ui.playlist_button.clicked.connect(
            lambda: (
                self.hide_all_widget(),
                self.ui.playlists.deselect(),
                ui_playlist.playlist.set_downloads_playlist_mode(),
                self.get_widget("playlist", 0).show(),
            )
        )
        self.ui.home_button.clicked.connect(
            lambda: (self.hide_all_widget(), self.get_widget("welcome_menu", 0).show())
        )

        ui_playlist.playlist.has_music.connect(
            lambda: (
                self.ui.pause_button.setEnabled(True),
                self.ui.backward_button.setEnabled(True),
                self.ui.forward_button.setEnabled(True),
            )
        )

        self.ui.pause_button.clicked.connect(
            lambda: (
                ui_playlist.playlist.resume(),
                self.ui.pause_button.hide(),
                self.ui.resume_button.show(),
            )
        )

        self.ui.resume_button.clicked.connect(
            lambda: (
                ui_playlist.playlist.pause(),
                self.ui.pause_button.show(),
                self.ui.resume_button.hide(),
            )
        )

        self.ui.forward_button.clicked.connect(ui_playlist.playlist.forward)
        self.ui.backward_button.clicked.connect(ui_playlist.playlist.backward)

        self.ui.progress_bar.setEnabled(False)
        ui_playlist.playlist.has_music.connect(
            lambda: (self.ui.progress_bar.setEnabled(True),)
        )
        ui_playlist.playlist.media_player.durationChanged.connect(
            lambda duration: (
                self.ui.progress_bar.blockSignals(True),
                self.ui.progress_bar.setMaximum(duration),
                self.ui.total_duration.setText(
                    QDateTime.fromMSecsSinceEpoch(duration).toString("m:ss")
                ),
                self.ui.progress_bar.blockSignals(False),
            ),
        )
        ui_playlist.playlist.media_player.positionChanged.connect(
            lambda position: (
                self.ui.progress_bar.blockSignals(True),
                self.ui.progress_bar.setSliderPosition(position),
                self.ui.duration_passed.setText(
                    QDateTime.fromMSecsSinceEpoch(position).toString("m:ss")
                ),
                self.ui.progress_bar.blockSignals(False),
            )
        )

        self.ui.progress_bar.valueChanged.connect(
            lambda value: (ui_playlist.playlist.media_player.setPosition(value),)
        )

        self.ui.progress_bar.setPageStep(10 * 1000)
        self.ui.progress_bar.setSingleStep(5 * 1000)

        self.ui.volume_bar.valueChanged.connect(
            lambda value: (ui_playlist.playlist.audio_output.setVolume(value / 100),)
        )
        self.ui.volume_bar.setValue(Settings.volume)

        self.ui.playbackmode_loop.clicked.connect(
            lambda: (
                self.ui.playbackmode_loop.hide(),
                self.ui.playbackmode_looponce.show(),
                ui_playlist.playlist.set_playback_mode(PlaybackMode.LoopOnce),
            )
        )

        self.ui.playbackmode_looponce.clicked.connect(
            lambda: (
                self.ui.playbackmode_looponce.hide(),
                self.ui.playbackmode_sequential.show(),
                ui_playlist.playlist.set_playback_mode(PlaybackMode.Sequential),
            )
        )

        self.ui.playbackmode_sequential.clicked.connect(
            lambda: (
                self.ui.playbackmode_sequential.hide(),
                self.ui.playbackmode_random.show(),
                ui_playlist.playlist.set_playback_mode(PlaybackMode.Random),
            )
        )

        self.ui.playbackmode_random.clicked.connect(
            lambda: (
                self.ui.playbackmode_random.hide(),
                self.ui.playbackmode_loop.show(),
                ui_playlist.playlist.set_playback_mode(PlaybackMode.Loop),
            )
        )

        self.ui.playlists.itemClicked.connect(
            lambda item: (
                self.hide_all_widget(),
                ui_playlist.playlist.save_current_playlist(),
                ui_playlist.playlist.load_from_playlist(item.text()),
                self.get_widget("playlist", 0).show(),
            )
        )

    def add_widget(self, ui, name: str):
        menu = QWidget(self.ui.main_menu)
        ui.setupUi(menu)
        self.vertical_layout.addWidget(menu)
        menu.hide()

        self.mainmenu_widgets[name] = (menu, ui)
        return ui

    def get_widget(self, name: str, index: int = 1):
        """
        get widget given by name

        index is the index which will give the widget, or the ui
        default is 1 so this function will return ui
        """
        return self.mainmenu_widgets[name][index]

    def hide_all_widget(self):
        """
        hide all the widgets that are possibly shown
        """
        for widget in self.mainmenu_widgets.values():
            widget[0].hide()

    def delete_cell_widgets(self):
        ui_search_menu: Ui_SearchMenu = self.get_widget("search_menu")
        for row in range(ui_search_menu.results.rowCount()):
            ui_search_menu.results.removeCellWidget(row, 0)
            ui_search_menu.results.removeCellWidget(row, 3)

    @pyqtSlot(dict)
    def done_search(self, search_result: dict):
        ui_search_menu: Ui_SearchMenu = self.get_widget("search_menu")
        ui_search_menu.results.show()
        ui_search_menu.searching_label.hide()

        ui_search_menu.results.setRowCount(0)
        self.delete_cell_widgets()

        start = time.perf_counter()

        for (index, result) in enumerate(search_result["result"]):
            link = result["link"] if "link" in result else None

            download_button = DownloadButton(link, self)
            download_button.clicked.connect(
                partial(self.start_download, download_button)
            )
            download_button.setMinimumWidth(400)

            ui_search_menu.results.insertRow(index)
            try:
                ui_search_menu.results.setItem(
                    index, 1, QTableWidgetItem(result["title"])
                )
                ui_search_menu.results.setItem(
                    index, 2, QTableWidgetItem(result["channel"]["name"])
                )
                ui_search_menu.results.setCellWidget(
                    index,
                    3,
                    download_button,
                )
            except Exception as error:
                logger.error("Cannot insert data! (Error: %s)", error)
                continue

        end = time.perf_counter()
        logger.debug(f"Time Elapsed: {end-start} seconds")

        self.image_loading_thread = QThread()
        self.image_loader = tasks.ImageLoader()
        self.image_loader.moveToThread(self.image_loading_thread)
        self.image_loader.done.connect(self.image_loading_thread.quit)
        self.image_loader.image_loaded.connect(
            lambda index: self.load_image(index, ui_search_menu.results)
        )

        self.image_loading_thread.started.connect(
            partial(
                self.image_loader.load_images,
                search_result,
                ui_search_menu.results.size(),
            )
        )
        self.image_loading_thread.start()

    @pyqtSlot(int, QTableWidget)
    def load_image(self, index: int, table_widget: QTableWidget):
        thumbnail = QLabel()
        thumbnail.setPixmap(self.image_loader.thumbnails[0])
        self.image_loader.thumbnails.pop()
        table_widget.setCellWidget(index, 0, thumbnail)
        table_widget.resizeRowsToContents()

    def start_search(self):
        if not self.ui.search_bar.text():
            return

        self.hide_all_widget()
        self.get_widget("search_menu", 0).show()

        ui_search_menu: Ui_SearchMenu = self.mainmenu_widgets["search_menu"][1]
        ui_search_menu.searching_label.setText(f"Searching {self.ui.search_bar.text()}")
        ui_search_menu.searching_label.show()
        ui_search_menu.results.hide()

        if self.image_loading_thread.isRunning():
            self.image_loader.interrupt = True
            self.image_loading_thread.quit()
        if self.search_thread.isRunning():
            self.search_thread.quit()

        self.search_thread = QThread()
        self.search_video = tasks.SearchVideo()
        self.search_video.moveToThread(self.search_thread)
        self.search_video.done.connect(self.search_thread.quit)
        self.search_video.result_ready.connect(self.done_search)
        self.search_video.error_occurred.connect(
            lambda error: (
                ui_search_menu.searching_label.setText(
                    f"Error occurred while searching: {error}"
                )
            )
        )

        self.search_thread.started.connect(
            partial(self.search_video.search, self.ui.search_bar.text())
        )
        self.search_thread.start()

        self.ui.search_bar.setDisabled(True)
        self.ui.search_button.setDisabled(True)
        QTimer.singleShot(
            1,
            lambda: (
                self.ui.search_bar.setEnabled(True),
                self.ui.search_button.setEnabled(True),
            ),
        )

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.search_thread.terminate()
        self.image_loading_thread.terminate()
        self.image_loader.interrupt = True

        playlist = self.get_widget("playlist").playlist
        Settings.save_settings(
            volume=self.ui.volume_bar.value(), playback_mode=playlist.playback_mode
        )

        playlist.save_downloads_playlist()
        playlist.save_current_playlist()

        return super().closeEvent(a0)

    def set_button_downloaded(self, button: QPushButton):
        try:
            button.setText("Downloaded!")
        except Exception:
            pass

    @pyqtSlot(str)
    def delete_thread(_, thread_id: str):
        logger.info(App.download_threads)
        logger.info(f"Deleting {thread_id}...")
        App.download_threads[thread_id][0].quit()
        logger.info("Quitted successful")
        del App.download_threads[thread_id]
        logger.info(App.download_threads)

    @pyqtSlot(DownloadButton)
    def start_download(self, button: DownloadButton):
        if pytube.YouTube(button.link).length >= 600:
            choice_button = QMessageBox.warning(
                self,
                "Warning",
                "You are about to download a video that is more than 10 minutes long. It might take a long time. Continue?",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            )
            if choice_button == QMessageBox.StandardButton.Cancel:
                return
        logger.debug(f"start download {button.link}")

        try:
            button.setText("Downloading...")
            button.setEnabled(False)
        except Exception as error:
            logger.error("cannot edit button! %s", error)

        App.video_download_manager.add_download(button.link)
        App.video_download_manager.done_downloading.connect(
            partial(self.set_button_downloaded, button)
        )
        App.video_download_manager.download()

    @pyqtSlot(str, Exception, bool)
    def done_downloading(self, link: str, error: Exception, error_exist: bool):
        video = pytube.YouTube(link)

        if error_exist:
            QMessageBox.warning(
                self,
                "Failed to download!",
                f"Failed to download {video.title} (Error: {error})",
            )
            return

        QMessageBox.information(
            self,
            "Done Downloading!",
            f'Video "{video.title}" has been successfully downloaded',
        )

    @pyqtSlot(str, QPushButton)
    def download_directly_from_url(self, url: str, button: QPushButton):
        try:
            video = pytube.YouTube(url)
        except Exception as error:
            QMessageBox.warning(
                self,
                "Failed to download!",
                f'Failed to download from url: "{url}" (Error: {error})',
            )
            return

        if video.length >= 600:
            choice_button = QMessageBox.warning(
                self,
                "Warning",
                "You are about to download a video that is more than 10 minutes long. It might take a long time. Continue?",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            )
            if choice_button == QMessageBox.StandardButton.Cancel:
                return
        logger.debug(f"start download {url}")

        try:
            button.setText("Downloading...")
            button.setEnabled(False)
        except Exception:
            pass

        App.video_download_manager.add_download(url)
        App.video_download_manager.done_downloading.connect(
            partial(self.set_button_downloaded, button)
        )
        App.video_download_manager.download()
