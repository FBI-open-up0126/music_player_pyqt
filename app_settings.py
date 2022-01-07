import logging

from PyQt6.QtGui import QColor


SEARCH_LIMIT = 15

LOGGING_LEVEL = logging.DEBUG
FORMAT = "[%(filename)s(%(lineno)s): %(levelname)s] %(funcName)s(): %(message)s"

DOWNLOAD_AUDIO_TO = "downloads"
DOWNLOADS_PLAYLIST = DOWNLOAD_AUDIO_TO

PLAYLIST_DIRECTORY = "./playlists/"
DOWNLOADS_DIRECTORY = "./downloads/"

YOUTUBE_PREFIX = "https://www.youtube.com/watch?v="

THUMBNAIL_FOLDER = "thumbnails/"
SETTINGS_FILE = "settings.json"

CURRENT_PLAYING_SONG_COLOR = QColor(0, 150, 0)

IMAGE_RESOURCES = ["resources/images/"] * 9
IMAGE_RESOURCES[0] += "backward.png"
IMAGE_RESOURCES[1] += "forward.png"
IMAGE_RESOURCES[2] += "loop.png"
IMAGE_RESOURCES[3] += "no-thumbnail.png"
IMAGE_RESOURCES[4] += "pause.png"
IMAGE_RESOURCES[5] += "random.png"
IMAGE_RESOURCES[6] += "repeat.png"
IMAGE_RESOURCES[7] += "resume.png"
IMAGE_RESOURCES[8] += "sequential.png"
