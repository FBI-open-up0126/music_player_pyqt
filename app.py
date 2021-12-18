from typing import Optional
from PyQt6 import QtCore
from PyQt6.QtCore import QObject, QThread, pyqtSlot
from PyQt6.QtWidgets import (
    QHeaderView,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
import youtubesearchpython as ytsearch
import datetime

from ui.app import Ui_App
from ui.search_menu import Ui_SearchMenu
from ui.welcome_menu import Ui_WelcomeMenu

SEARCH_LIMIT = 20


class MyPushButton(QPushButton):
    def __init__(
        self,
    ):
        super().__init__("Download!")


class SearchVideo(QObject):
    done = QtCore.pyqtSignal()

    def search(self, search_text) -> None:
        try:
            self.search_results = ytsearch.Search(
                search_text, limit=SEARCH_LIMIT, timeout=10
            ).result()
        except Exception as error:
            print(f"No Internet Connection Avaliable! (Error: {type(error).__name__})")
            self.done.emit()
            return

        print(self.search_results)
        self.done.emit()


class App(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # initialize variables
        self.ui = Ui_App()
        self.ui.setupUi(self)

        self.mainmenu_widgets: dict[str, tuple[QWidget, object]] = {}

        self.vertical_layout = QVBoxLayout(self.ui.main_menu)
        self.vertical_layout.setSpacing(0)
        self.vertical_layout.setContentsMargins(0, 0, 0, 0)

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

    def done_search(self, search_result: dict):
        # try:
        #     self.search_results = ytsearch.Search(
        #         self.ui.search_bar.text(), limit=SEARCH_LIMIT, timeout=10
        #     ).result()["result"]
        # except Exception as error:
        #     print(f"No Internet Connection Avaliable! (Error: {type(error).__name__})")
        #     return

        print(search_result == None)
        ui_search_menu: Ui_SearchMenu = self.get_widget("search_menu")
        ui_search_menu.results.show()
        ui_search_menu.searching_label.hide()

        total_search = SEARCH_LIMIT

        for (index, result) in enumerate(search_result["result"]):
            if not "title" in result or not "channel" in result:
                total_search = index
                break

            ui_search_menu.results.insertRow(index)

            ui_search_menu.results.setItem(index, 0, QTableWidgetItem(result["title"]))
            ui_search_menu.results.setItem(
                index, 1, QTableWidgetItem(result["channel"]["name"])
            )
            ui_search_menu.results.setCellWidget(index, 2, QPushButton("Hello, world!"))

        # ui_search_menu.results.setRowCount(total_search)

    def start_search(self):
        if not self.ui.search_bar.text():
            return

        ui_search_menu: Ui_SearchMenu = self.mainmenu_widgets["search_menu"][1]
        ui_search_menu.searching_label.setText(f"Searching {self.ui.search_bar.text()}")
        ui_search_menu.searching_label.show()
        ui_search_menu.results.hide()

        self.mainmenu_widgets["search_menu"][0].show()
        self.mainmenu_widgets["welcome_menu"][0].hide()

        thread = QThread()
        search_video = SearchVideo()
        search_video.moveToThread(thread)
        # search_video.done.connect(thread.quit)
        thread.started.connect(lambda: search_video.search(self.ui.search_bar.text()))
        thread.finished.connect(lambda: self.done_search(search_video.search_results))
        thread.start()

        # thread = threading.Thread(target=self.search)
        # thread.start()
