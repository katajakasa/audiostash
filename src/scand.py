# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime
import mutagen
import argparse
import signal
from common.stashlog import StashLog
from common.tables import \
    database_init, database_ensure_initial, session_get, \
    Track, Album, Directory, Artist, Cover, Log
from common.utils import decode_path, match_track_filename, get_or_create
import settings
from twisted.internet import reactor
from sqlalchemy.orm.exc import NoResultFound

_ver = "v0.1"
_name = "Audiostash Indexer Daemon " + _ver

# Handle arguments
parser = argparse.ArgumentParser(description=_name)
parser.add_argument('-i', '--initial', action="store_true", default=False, help='Do an initial scan and conversion.')
args = parser.parse_args()
is_initial = args.initial


class Scanner(object):
    @staticmethod
    def _get_tag(m, keys):
        for tag in keys:
            try:
                return unicode(m[tag][0])
            except KeyError:
                pass
            except ValueError:
                pass
        return u''

    @staticmethod
    def _get_tag_int(m, keys):
        for tag in keys:
            try:
                return int(m[tag][0])
            except KeyError:
                pass
            except ValueError:
                pass
        return None

    # TODO: Better tag lookup
    # TODO: Use subsessions for track components (artist, etc)
    def handle_audio(self, path, ext):
        s = session_get()

        # Return here if track already exists for this path
        if s.query(Track).filter_by(file=path).count() > 0:
            return
        
        m = None
        try:
            m = mutagen.File(path)
        except:
            self.log.warning(u"Could not read header for {}".format(path))

        # Create a new entry for track
        track = Track(file=path, album=1, artist=1)

        if m:
            # Find artist
            track_artist = self._get_tag(m, ('TPE1', u'©ART', 'Author', 'Artist', 'ARTIST',
                                             'TRACK ARTIST', 'TRACKARTIST', 'TrackArtist', 
                                             'Track Artist'))

            # Find album artist
            album_artist = self._get_tag(m, ('TPE2', u'aART', 'TXXX:ALBUM ARTIST', 'ALBUM ARTIST', 'ALBUMARTIST',
                                             'AlbumArtist', 'Album Artist'))

            # Find album title
            album_title = self._get_tag(m, (u'©alb', 'TALB', 'ALBUM', 'album'))
            
            # Find title
            track_title = self._get_tag(m, (u'©nam', 'TIT2', 'Title', 'TITLE', 'TRACK TITLE',
                                            'TRACKTITLE', 'TrackTitle', 'Track Title'))

            # Find track
            track.track = self._get_tag_int(m, ('TRCK', 'Track', 'TRACK', 'TRACK', 'TRACKNUMBER'))
            
            # Find date
            track.date = self._get_tag_int(m, ('TYER', 'TDAT', "DATE", "YEAR", "Date", "Year"))
            if track.date is None:
                track.date = u""
            
            # Set track title, if found
            if track_title:
                track.title = track_title
            elif track.track and album_title:
                track.title = album_title + u" " + str(track.track)
            elif track.track:
                track.title = "Track " + str(track.track)
            else:
                track.title = os.path.splitext(os.path.basename(path))[0]
            
            # If there is a track artist, add it to its own model
            if track_artist:
                artist = get_or_create(s, Artist, name=track_artist)
                track.artist = artist.id
            elif album_artist:
                artist = get_or_create(s, Artist, name=album_artist)
                track.artist = artist.id

            # If there is no track title or artist, try to parse the filename
            if not track.title or not track.artist:
                filename = os.path.splitext(os.path.basename(path))[0]
                m_artist, m_title = match_track_filename(filename)
                if not track.title and m_title:
                    track.title = m_title
                if not track.artist and m_artist:
                    track.artist = m_artist

            # Looks for album with given information
            if album_title:
                if album_artist:
                    a_artist = get_or_create(s, Artist, name=album_artist)
                else:
                    a_artist = s.query(Artist).get(1)
                
                # Set album
                try:
                    album = s.query(Album).filter_by(title=album_title, artist=a_artist.id).one()
                    track.album = album.id
                except NoResultFound:
                    album = Album(title=album_title, artist=a_artist.id, cover=1)
                    s.add(album)
                    s.commit()
                    track.album = album.id

        # Set dir
        bpath = os.path.dirname(path)
        mdir = get_or_create(s, Directory, directory=bpath)
        track.dir = mdir.id
                 
        # Save everything
        s.add(track)
        s.commit()

    def postprocess_deleted(self):
        s = session_get()

        self.log.debug(u"Removing deleted tracks from database ...")
        for track in s.query(Track):
            if not os.path.isfile(track.file):
                self.handle_track_delete(track)
        self.log.debug(u"Removing deleted covers from database ...")
        for cover in s.query(Cover):
            if cover.id == 1:
                continue
            if not os.path.isfile(cover.file):
                self.handle_cover_delete(cover)

    def postprocess_albums(self):
        self.log.debug(u"Postprocessing albums ...")
        s = session_get()
        found = 0
        for album in s.query(Album):
            # Stop if quite is requested
            if not self._run:
                s.rollback()
                return
            # Just jump over PK 1, this is the unknown album
            if album.id == 1:
                continue
            # skip albums that already have an artist
            if album.artist != 1:
                continue

            # See if all tracks in album have matching artist
            test = None
            found_artist = True
            for track in s.query(Track).filter_by(album=album.id):
                if test is None:
                    test = track.artist
                else:
                    if test != track.artist:
                        found_artist = False

            if found_artist:
                # If we got here, all tracks in the album had the same artist.
                # Therefore, set album artist as this.
                found += 1
                album.artist = test

        s.commit()
        self.log.debug(u"Found artist for {} new albums".format(found))
            
    def postprocess_covers(self):
        self.log.debug(u"Postprocessing covers ...")
        s = session_get()
        found = 0
        for album in s.query(Album):
            # Stop if quit is requested
            if not self._run:
                s.rollback()
                return
            # If album already has a cover, keep going
            if album.cover != 1:
                continue
            # Jump over PK 1, this is the unknown album
            if album.id == 1:
                continue

            # Try to find cover art for this album
            for track in s.query(Track).filter_by(album=album.id):
                mdir = s.query(Directory).get(track.dir)
                cover_art = self._cover_art.get(mdir.directory, None)
                if cover_art:
                    cover = get_or_create(s, Cover, file=cover_art[0])
                    album.cover = cover.id
                    found += 1
                    break

        s.commit()
        self._cover_art = {}  # Clear cover art cache
        self.log.debug(u"Found and attached {} new covers.".format(found,))

    def handle_cover(self, path, ext):
        name = os.path.splitext(os.path.basename(path))[0]
        mdir = os.path.dirname(path)
        prev = [None, 0]

        # Get the previous cover art
        if mdir in self._cover_art:
            prev = self._cover_art[mdir]

        # If this seems like cover art, handle it.
        # Naively expect that if filesize is larger, the quality is better
        # TODO: Do this properly with eg. pillow
        for hint in settings.COVER_HINTS:
            if hint in name.lower():
                size = os.path.getsize(path)
                if size > prev[1]:
                    prev = [path, size]

        # Found cover art, save it for now
        if prev[0]:
            self._cover_art[mdir] = prev

    def handle_track_delete(self, track):
        self.log.debug(u"Deleting track {} ...".format(track.file))
        s = session_get()
        
        if track.album != 1:
            # If album only has a single (this) track, remove album
            if s.query(Track).filter_by(album=track.album).count() == 0:
                s.query(Album).get(track.album).delete()
                
        if track.artist != 1:
            # If artist only has a single (this) track, remove artist
            if s.query(Track).filter_by(artist=track.artist).count() == 0:
                s.query(Artist).get(track.artist).delete()

        # That's that, delete the track.
        s.query(Track).get(track.id).delete()

        # Save changes
        s.commit()

    def handle_cover_delete(self, cover):
        self.log.debug(u"Deleting cover {} ...".format(cover.file))
        s = session_get()
        for album in s.query(Album).filter_by(cover=cover.id):
            album.cover = 1
        s.query(Cover).get(cover.id).delete()
        s.commit()
            
    def handle_delete(self, path):
        track = None
        cover = None
        
        # If it does NOT, make sure it is removed from index
        # First, see if track exists with this path. If not, see if it is a cover.
        # If neither, stop here.
        s = session_get()
        try:
            track = s.query(Track).filter_by(file=path).one()
        except NoResultFound:
            try:
                cover = s.query(Cover).filter_by(file=path).one()
            except NoResultFound:
                return

        # If we found a cover, remove it and clear references to it from albums
        if cover:
            self.handle_cover_delete(cover)
            return

        # If we found a track, remove it from any albums. If the albums are now empty, remove them.
        # If artist does not belong to any track, remove it also
        if track:
            self.handle_track_delete(track)
            return

    def handle_file(self, path):
        ext = os.path.splitext(path)[1]
        
        if os.path.isfile(path):
            # If file exists, scan it
            if ext in settings.DAEMON_SCAN_FILES:
                self.handle_audio(path, ext)
            if ext in settings.COVER_EXTENSIONS:
                self.handle_cover(path, ext)
        else:
            self.handle_delete(path)

    def traverse_dir(self, directory):
        for dir_name, subdir_list, file_list in os.walk(directory):
            if not self._run:
                return

            self._dirs += 1

            # Handle all files in this directory
            for mfile in file_list:
                if not self._run:
                    return
                full_path = os.path.join(decode_path(dir_name), decode_path(mfile))
                self._files += 1
                if self._files % 500 == 0:
                    self.log.debug("{} files handled.".format(self._files))
                self.handle_file(full_path)

            # Handle subdirs
            for mdir in subdir_list:
                self.traverse_dir(mdir)

    def process_files(self):
        self.log.info(u"Scanning directory " + settings.MUSIC_DIRECTORY)
        self._files = 0
        self._dirs = 0
        self._cover_art = {}
        self.traverse_dir(settings.MUSIC_DIRECTORY)
        self.log.info(u"Found {} files in {} directories.".format(self._files, self._dirs))

    def clean_db(self):
        self.log.info(u"Clearing old data ...")
        s = session_get()
        s.query(Track).delete()
        s.query(Album).delete()
        s.query(Directory).delete()
        s.query(Artist).delete()
        s.query(Cover).delete()
        s.commit()
        database_ensure_initial()

    def scan_all(self):
        self.log.info(u"Scanning ...")
        self.process_files()
        self.postprocess_deleted()
        self.postprocess_albums()
        self.postprocess_covers()
        self.log.info(u"Scan complete")

    def __init__(self, log=None, cleanup=False):
        self.log = log
        self.log.info(_name)
        self._cover_art = {}  # Save found cover files here
        self._files = 0
        self._dirs = 0
        self._run = True

        # If doing a re-indexing
        s = session_get()
        if cleanup or s.query(Track).count() == 0:
            self.clean_db()

    def run(self):
        self.log.info("Initial scan ...")
        self.scan_all()
        self.log.debug(u"Waiting for events ...")
        reactor.run()
        self.log.debug(u'All done.')

    def stop(self):
        self._run = False
        reactor.stop()
        self.log.info("Quitting ...")


def sig_handler(signum, frame):
    scanner.log.info(u"Caught signal {}, quitting ...".format(signum))
    scanner.stop()

if __name__ == '__main__':
    log = StashLog(debug=settings.DEBUG, level=settings.LOG_LEVEL, logfile=settings.STASH_LOGFILE)

    # Init database and bootstrap the scanner
    database_init(settings.DBFILE)
    scanner = Scanner(log=log, cleanup=is_initial)

    # There should be okay on windows ...
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    # ... while these are not. Try for linux' sake, though.
    try:
        signal.signal(signal.SIGHUP,  sig_handler)
        signal.signal(signal.SIGQUIT, sig_handler)
    except AttributeError:
        pass

    # Just run as long as possible, then exit with 0 status.
    scanner.run()
    exit(0)
