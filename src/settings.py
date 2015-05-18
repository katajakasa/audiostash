# -*- coding: utf-8 -*-

# Find basedir
import os
BASEDIR = os.path.dirname(os.path.abspath(__file__))

# Feel free to change these
PORT = 8000  # Port for the server.
DEBUG = True  # Debug mode. Should be True for developing, False otherwise.
MUSIC_DIRECTORY = "Z:\\"  # Where your music can be found

# Cover filename hints (looks for eg. cover_*.<ext> in album path.
COVER_HINTS = [
    'cover',
    'album',
    'front',
    'folder',
    'index'
]

# Cover extensions to scan
COVER_EXTENSIONS = [
    '.png',
    '.jpg',
    '.jpeg'
]

# Audiofile extensions to scan
DAEMON_SCAN_FILES = [
    '.mp3',
    '.ogg',
    '.flac',
    '.aac',
    '.opus',
    '.m4a',
    '.m4b',
    '.wav'
]

# Logfile for the daemon. If debugmode is on and this is None, then stdout will be used for log output.
# If this value points to a logfile, that will be used.
# If debugmode is off and this is None, only database log will be used.
LOGFILE = None
# LOGFILE = "/var/log/audiostash.log"

# Database file location. Currently only sqlite3 is supported.
DBFILE = os.path.join(BASEDIR, "audiostash.db")

# No point in changing these
STATIC_PATH = os.path.join(BASEDIR, "static")
TEMPLATE_PATH = os.path.join(BASEDIR, "tpl")
