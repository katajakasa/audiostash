# -*- coding: utf-8 -*-

# Find basedir
import os
BASEDIR = os.path.dirname(os.path.abspath(__file__))

# Port for the server.
PORT = 5961

# Debug mode.
# If true, the daemons will print on commandline instead of logfile.
# Set False for production, True for development.
DEBUG = True

# Where your music can be found
MUSIC_DIRECTORY = "Z:\\"

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
LOG_LEVEL = 0

# Database file location. Currently only sqlite3 is supported.
DBFILE = os.path.join(BASEDIR, "audiostash.db")

# No point in changing these
PUBLIC_PATH = os.path.join(BASEDIR, "public")
