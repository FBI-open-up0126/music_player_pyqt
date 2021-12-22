import time
import datetime
import logging
import string
import pytube
import tasks
import random

from PyQt6.QtCore import QThread, QThreadPool, pyqtSlot
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from functools import partial
from ui.app import Ui_App
from ui.search_menu import Ui_SearchMenu
from ui.welcome_menu import Ui_WelcomeMenu
from my_widget import DownloadButton
from PyQt6 import QtGui
from app_settings import FORMAT, LOGGING_LEVEL

logging.basicConfig(format=FORMAT, level=LOGGING_LEVEL)
logger = logging.getLogger(__name__)


def id_generator(size=6, chars=string.ascii_uppercase + string.digits) -> str:
    return "".join(random.choice(chars) for _ in range(size))


class App(QWidget):
    download_threads: dict[str, tuple[QThread, tasks.VideoDownloadManager]] = {}
    video_download_manager = tasks.VideoDownloadManager()

    def __init__(self, parent=None):
        super().__init__(parent)

        # initialize variables
        self.ui = Ui_App()
        self.ui.setupUi(self)

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

        self.pool = QThreadPool()

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
        ui_search_menu.results.verticalScrollBar().setSingleStep(20)

        self.get_widget("welcome_menu", 0).show()

        # initialize connections
        self.ui.search_button.clicked.connect(self.start_search)
        self.ui.search_bar.returnPressed.connect(self.start_search)

    def add_widget(self, ui, name: str):
        menu = QWidget(self.ui.main_menu)
        ui_menu = ui
        ui_menu.setupUi(menu)
        self.vertical_layout.addWidget(menu)
        menu.hide()

        self.mainmenu_widgets[name] = (menu, ui_menu)
        return ui_menu

    def get_widget(self, name: str, index: int = 1):
        """
        get widget given by name

        index is the index which will give the widget, or the ui
        default is 1 so this function will return ui
        """
        return self.mainmenu_widgets[name][index]

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
        self.image_loader.image_loaded.connect(self.load_image)

        self.image_loading_thread.started.connect(
            partial(self.image_loader.load_images, search_result, self.size())
        )
        self.image_loading_thread.start()

    @pyqtSlot(int)
    def load_image(self, index: int):
        thumbnail = QLabel()
        thumbnail.setPixmap(self.image_loader.thumbnails[0])
        self.image_loader.thumbnails.pop()
        ui_search_menu: Ui_SearchMenu = self.get_widget("search_menu")
        ui_search_menu.results.setCellWidget(index, 0, thumbnail)
        ui_search_menu.results.resizeRowsToContents()
        pass

    def start_search(self):
        if not self.ui.search_bar.text():
            return

        ui_search_menu: Ui_SearchMenu = self.mainmenu_widgets["search_menu"][1]
        ui_search_menu.searching_label.setText(f"Searching {self.ui.search_bar.text()}")
        ui_search_menu.searching_label.show()
        ui_search_menu.results.hide()

        self.mainmenu_widgets["search_menu"][0].show()
        self.mainmenu_widgets["welcome_menu"][0].hide()

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

        self.search_thread.started.connect(
            partial(self.search_video.search, self.ui.search_bar.text())
        )
        self.search_thread.start()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.search_thread.terminate()
        self.image_loading_thread.terminate()
        self.image_loader.interrupt = True

        return super().closeEvent(a0)

    def set_button_downloaded(self, button: DownloadButton):
        try:
            button.setText("Downloaded!")
            # button.setEnabled(True)
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

    @pyqtSlot(str)
    def done_downloading(self, link: str):
        video = pytube.YouTube(link)

        QMessageBox.information(
            self,
            "Done Downloading!",
            f"Video {video.title} has been successfully downloaded",
        )
