# -*- coding: utf-8 -*-

# Find basedir
import os
BASEDIR = os.path.dirname(os.path.abspath(__file__))

# Port for the server.
PORT = 8000

# Debug mode.
# If true, the daemons will print on commandline instead of logfile.
# Set False for production, True for development.
DEBUG = False

# Where your music can be found
# On windows, please use slashes instead of backslashes (eg. C:/music/)
MUSIC_DIRECTORY = "/mnt/music"

# Where your audiobooks can be found (None if doesn't exist)
# On windows, please use slashes instead of backslashes (eg. C:/music/)
AUDIOBOOK_DIRECTORY = None

# Image cache directory
# Make sure this is not inside or the same as MUSIC_DIRECTORY
COVER_CACHE_DIRECTORY = '/mnt/tmp/cover'

# Transcoded file cache directory (Reserve plenty of space!)
# Make sure this is not inside or the same as MUSIC_DIRECTORY
MUSIC_CACHE_DIRECTORY = '/mnt/tmp/music'

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

# Don't transcode these (Note: Without prefix dot!)
NO_TRANSCODE_FORMATS = [
    'mp3',
    'ogg'
]

# Format to transcode to
# Note: Currently does not work with other formats! Do not change!
TRANSCODE_FORMAT = 'mp3'

# Logfile for the daemon. If debugmode is on, then stdout will be used for log output.
# If this value points to a logfile, that will be used.

# STASH_LOGFILE = "/var/log/audiostash.log"
STASH_LOGFILE = None

# SCAND_LOGFILE = "/var/log/audiostash-scand.log"
SCAND_LOGFILE = None

# Level 0 = Debug|Info|Warning|Error
# Level 1 = Info|Warning|Error
# Level 2 = Warning|Error
# Level 3 = Error
LOG_LEVEL = 1

# Database file location. Currently only sqlite3 is supported.
DBFILE = os.path.join(BASEDIR, "audiostash.db")

# No point in changing these
PUBLIC_PATH = os.path.join(BASEDIR, "public")
