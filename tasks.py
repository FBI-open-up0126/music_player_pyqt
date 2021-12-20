import logging
import youtubesearchpython as ytsearch
import urllib.request as urlreq

from PyQt6.QtCore import QObject, QSize
from PyQt6 import QtCore
from main import LOGGING_LEVEL, FORMAT
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

logging.basicConfig(level=LOGGING_LEVEL, format=FORMAT)
logger = logging.getLogger(__name__)

SEARCH_LIMIT = 15


class SearchVideo(QObject):
    done = QtCore.pyqtSignal()
    result_ready = QtCore.pyqtSignal(dict)

    def search(self, search_text):
        try:
            search_results = ytsearch.Search(
                search_text, limit=SEARCH_LIMIT, timeout=10
            ).result()
            self.result_ready.emit(search_results)
        except Exception as error:
            logger.error(
                f"No Internet Connection Avaliable! (Error: %s)", error, exc_info=1
            )
            return
        finally:
            self.done.emit()


class ImageLoader(QObject):
    done = QtCore.pyqtSignal()
    image_loaded = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.thumbnails = []
        self.interrupt = False

    def load_images(self, search_result: dict, widget_size: QSize):
        self.search_result = search_result
        self.widget_size = widget_size
        self.thumbnails.clear()

        for index, result in enumerate(search_result["result"]):
            if self.interrupt:
                self.done.emit()
                return

            try:
                data = urlreq.urlopen(result["thumbnails"][0]["url"]).read()
                image = QPixmap()
                image.loadFromData(data)
                self.thumbnails.append(image)
            except Exception as error:
                logger.error("Failed to load image! (Error: %s)", error)
                self.thumbnails.append(QPixmap())
                self.image_loaded.emit(index)
                continue
            logger.debug(f"index added: {index}")
            self.image_loaded.emit(index)

        self.done.emit()
