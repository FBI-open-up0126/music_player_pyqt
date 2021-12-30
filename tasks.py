import logging
import os
import pytube
import youtubesearchpython as ytsearch
import urllib.request as urlreq
import json

from PyQt6.QtCore import QObject, QSize, QThread, Qt
from PyQt6 import QtCore
from app_settings import DOWNLOAD_AUDIO_TO, DOWNLOADS_PLAYLIST, FORMAT, LOGGING_LEVEL, PLAYLIST_DIRECTORY, SEARCH_LIMIT, SETTINGS_FILE, THUMBNAIL_FOLDER, YOUTUBE_PREFIX
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QMessageBox, QWidget

from my_widget import Playlist

logging.basicConfig(level=LOGGING_LEVEL, format=FORMAT)
logger = logging.getLogger(__name__)


class SearchVideo(QObject):
    done = QtCore.pyqtSignal()
    error_occurred = QtCore.pyqtSignal(Exception)
    result_ready = QtCore.pyqtSignal(dict)

    def search(self, search_text):
        try:
            search_results = ytsearch.VideosSearch(
                search_text, limit=SEARCH_LIMIT, timeout=10
            ).result()
            self.result_ready.emit(search_results)
        except Exception as error:
            logger.error("No Internet Connection Avaliable! (Error: %s)", error)
            self.error_occurred.emit(error)
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
        self.thumbnails.clear()

        for index, result in enumerate(search_result["result"]):
            if self.interrupt:
                self.done.emit()
                return

            try:
                url = result["thumbnails"][0]["url"]
                data = urlreq.urlopen(url).read()

                image = QPixmap()
                image.loadFromData(data)

                height_to_width_ratio = image.height() / image.width()
                reduced_width = int(widget_size.width() / 4)
                reduced_height = int(reduced_width * height_to_width_ratio)

                image = image.scaled(reduced_width, reduced_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.thumbnails.append(image)
                
            except Exception as error:
                logger.error("Failed to load image! (Error: %s)", error)
                self.thumbnails.append(QPixmap())
                self.image_loaded.emit(index)
                continue

            self.image_loaded.emit(index)

        self.done.emit()


class VideoDownloadManager(QObject):
    done = QtCore.pyqtSignal()
    done_downloading = QtCore.pyqtSignal(bytes, str, Exception, bool)
    download_thread = QThread()
    downloader = None

    def __init__(self):
        QObject.__init__(self)
        
        VideoDownloadManager.downloader = VideoDownload(self)

    def download(self):
        Self = VideoDownloadManager

        if Self.download_thread.isRunning():
            return

        Self.download_thread = QThread()

        Self.downloader.moveToThread(Self.download_thread)
        self.done.connect(Self.download_thread.quit)

        self.download_thread.started.connect(Self.downloader.start_download)
        self.download_thread.start()

    def add_download(self, link: str):
        VideoDownloadManager.downloader.download_list.append(link)

        
class VideoDownload(QObject):
    download_list: list[str] = list()

    def __init__(self, manager: VideoDownloadManager) -> None:
        super().__init__()
        
        self.manager = manager

    def start_download(self):
        Self = VideoDownload
        while Self.download_list:
            logger.info(f"download list links: {Self.download_list}")
            link = Self.download_list[0]
            try:
                logger.info(f"Starting to download {link}")
                video = pytube.YouTube(link)
                stream = video.streams.get_audio_only()
                stream.download(
                    DOWNLOAD_AUDIO_TO,
                    skip_existing=False,
                    filename=video.video_id,
                )
                logger.info("Downloaded Successful!")
                
                data = urlreq.urlopen(video.thumbnail_url).read()
                
                with open(THUMBNAIL_FOLDER + video.video_id, mode="wb+") as file:
                    file.write(data)
                
            except Exception as error:
                logger.error("Error while downloading video: %s", error)
                self.manager.done_downloading.emit(bytes(), link, error, True)
                continue
            self.manager.done_downloading.emit(data, link, Exception(), False)
            self.download_list.pop(0)

        self.manager.done.emit()


class PlaylistLoader(QObject):
    done_loading = QtCore.pyqtSignal()
    error_occurred = QtCore.pyqtSignal(Exception)
    item_loaded = QtCore.pyqtSignal(bytes, str, str)

    def __init__(self, playlist_widget: Playlist, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.playlist_widget = playlist_widget

    def load(self, playlist_name: str):
        is_downloads_playlist = self.playlist_widget.is_downloads_playlist
        playlist_name = PLAYLIST_DIRECTORY + playlist_name
        if is_downloads_playlist:
            playlist_name = DOWNLOADS_PLAYLIST

        match is_downloads_playlist:
            case True: 
                if not os.path.isdir(playlist_name):
                    os.makedirs(DOWNLOADS_PLAYLIST)
            case False:
                if not os.path.exists(PLAYLIST_DIRECTORY + playlist_name):
                    QMessageBox.warning(
                        self.playlist_widget.top_widget,
                        f"Playlist \"{playlist_name}\" does not exist".title(),
                        f"Playlist \"{playlist_name}\" does not exist! Check if you accidentally delete it or what!",
                    )
                    
        match is_downloads_playlist:
            case True:
                for filename in os.listdir(playlist_name):
                    url = YOUTUBE_PREFIX + filename
                    try:
                        video = pytube.YouTube(url)
                        
                        self.playlist_widget.referenced_url.append(video.video_id);
                        
                        with open(THUMBNAIL_FOLDER + video.video_id, "rb") as file:
                            image_data = file.read()
                        
                        self.item_loaded.emit(image_data, video.title, video.author)
                    except Exception as error:
                        logger.error("Something went wrong! %s", error)
                        self.error_occurred.emit(error)
            case False:
                ...
        
        self.done_loading.emit()
        
class Settings:
    volume: int = 30
        
    @classmethod
    def read_settings(cls):
        if not os.path.exists(SETTINGS_FILE):
            return
        
        with open(SETTINGS_FILE, mode="r") as file:
            json_data = file.read()
            json_data: dict = json.loads(json_data)
            cls.volume = json_data.get("volume", cls.volume)
        
    @classmethod
    def save_settings(cls):
        json_data = {
            "volume": cls.volume,
        }
        json_data = json.dumps(json_data, indent=2)
        logger.debug(json_data)
        
        with open(SETTINGS_FILE, mode="w+") as file:
            file.write(json_data)
        
    @classmethod
    def set_volume(cls, volume: int):
        cls.volume = volume