import logging
import pytube
import youtubesearchpython as ytsearch
import urllib.request as urlreq

from PyQt6.QtCore import QObject, QRunnable, QSize, QThread
from PyQt6 import QtCore
from app_settings import FORMAT, LOGGING_LEVEL, SEARCH_LIMIT
from PyQt6.QtGui import QPixmap

logging.basicConfig(level=LOGGING_LEVEL, format=FORMAT)
logger = logging.getLogger(__name__)


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

            self.image_loaded.emit(index)

        self.done.emit()


class VideoDownloadManager(QObject):
    class VideoDownload(QObject):
        download_list: list[str] = list()
        done = QtCore.pyqtSignal()
        done_downloading = QtCore.pyqtSignal(str)

        def __init__(self) -> None:
            super().__init__()

        def start_download(self):
            Self = VideoDownloadManager.VideoDownload
            while Self.download_list:
                logger.info(f"download list links: {Self.download_list}")
                try:
                    link = Self.download_list[0]
                    logger.info(f"Starting to download {link}")
                    video = pytube.YouTube(link)
                    stream = video.streams.get_audio_only()
                    stream.download("audio_downloads", skip_existing=False)
                    logger.info("Downloaded Successful!")
                except Exception as error:
                    logger.error("Error while downloading video: %s", error)
                self.done_downloading.emit(link)
                self.download_list.pop(0)

            self.done.emit()

    done = QtCore.pyqtSignal()
    done_downloading = QtCore.pyqtSignal(str)
    download_thread = QThread()
    downloader = VideoDownload()

    def __init__(self):
        QObject.__init__(self)

    def download(self):
        Self = VideoDownloadManager

        if Self.download_thread.isRunning():
            return

        Self.download_thread = QThread()

        Self.downloader.moveToThread(Self.download_thread)
        Self.downloader.done.connect(Self.download_thread.quit)
        Self.downloader.done.connect(self.done.emit)
        Self.downloader.done_downloading.connect(self.done_downloading.emit)

        Self.download_thread.started.connect(Self.downloader.start_download)
        Self.download_thread.start()

    def add_download(self, link: str):
        VideoDownloadManager.downloader.download_list.append(link)
