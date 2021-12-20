import time
import datetime
import logging
import tasks
import gc

from PyQt6.QtCore import QThread, pyqtSlot
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from functools import partial
from main import FORMAT, LOGGING_LEVEL
from ui.app import Ui_App
from ui.search_menu import Ui_SearchMenu
from ui.welcome_menu import Ui_WelcomeMenu
from my_widget import DownloadButton
from pympler.tracker import SummaryTracker

SEARCH_LIMIT = 15

logging.basicConfig(format=FORMAT, level=LOGGING_LEVEL)
logger = logging.getLogger(__name__)


class App(QWidget):
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

        start = time.perf_counter()

        self.delete_cell_widgets()

        for (index, result) in enumerate(search_result["result"]):
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
                    DownloadButton(result["link"] if "link" in result else None, self),
                )
            except Exception as error:
                logger.error("Cannot insert data! (Error: %s)", error)
                continue

        end = time.perf_counter()
        logger.info(f"Time Elapsed: {end-start} seconds")

        self.image_loading_thread.requestInterruption()
        self.image_loader.interrupt = True
        while self.image_loading_thread.isRunning():
            logger.debug("Thread is not stopping!")
            time.sleep(1)

        self.image_loading_thread = QThread()
        self.image_loader = tasks.ImageLoader()
        self.image_loader.moveToThread(self.image_loading_thread)
        self.image_loader.done.connect(self.image_loading_thread.quit)
        self.image_loader.image_loaded.connect(self.load_image)

        self.image_loading_thread.started.connect(
            partial(self.image_loader.load_images, search_result, self.size())
        )
        self.image_loading_thread.start()

        ui_search_menu.results.resizeRowsToContents()

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

        # self.image_loading_thread.quit()
        # self.search_thread.quit()

        self.mainmenu_widgets["search_menu"][0].show()
        self.mainmenu_widgets["welcome_menu"][0].hide()

        self.search_thread = QThread()
        self.search_video = tasks.SearchVideo()
        self.search_video.moveToThread(self.search_thread)
        self.search_video.done.connect(self.search_thread.quit)
        self.search_video.result_ready.connect(self.done_search)

        self.search_thread.started.connect(
            partial(self.search_video.search, self.ui.search_bar.text())
        )
        self.search_thread.start()
