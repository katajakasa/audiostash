# -*- coding: utf-8 -*-

import os
import mutagen
import logging

from audiostash.common import audiotranscode
from audiostash.common.tables import \
    database_ensure_initial, session_get, \
    Track, Album, Directory, Artist, Cover, Playlist
from audiostash.common.utils import decode_path, match_track_filename, get_or_create, utc_now
from audiostash import settings
from twisted.internet import reactor, task
from sqlalchemy.orm.exc import NoResultFound
from PIL import Image

log = logging.getLogger(__name__)


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
    def handle_audio(self, path, ext, is_audiobook):
        s = session_get()

        # If track already exists and has not changed, stop here
        # Otherwise either edit or create new track entry
        fsize = os.path.getsize(path)
        try:
            track = s.query(Track).filter_by(file=path).one()
            if fsize == track.bytes_len:
                return
        except NoResultFound:
            track = Track(file=path, album=1, artist=1, type=ext[1:])

        # Attempt to open up the file in Mutagen for tag information
        m = None
        try:
            m = mutagen.File(path)
        except:
            log.warning(u"Could not read header for %s", path)

        # Set correct sizes
        track.bytes_len = fsize
        track.bytes_tc_len = 0

        if m:
            # Find artist
            track_artist = self._get_tag(m, ('TPE1', u'©ART', 'Author', 'Artist', 'ARTIST', 'TXXX:ARTIST'
                                             'TRACK ARTIST', 'TRACKARTIST', 'TrackArtist', 'Track Artist',
                                             'artist'))

            # Find album artist
            album_artist = self._get_tag(m, ('TPE2', u'aART', 'TXXX:ALBUM ARTIST', 'TXXX:ALBUMARTIST', 'ALBUM ARTIST',
                                             'ALBUMARTIST', 'AlbumArtist', 'Album Artist'))

            # Find album title
            album_title = self._get_tag(m, (u'©alb', 'TALB', 'ALBUM', 'album', 'TXXX:ALBUM'))
            
            # Find title
            track_title = self._get_tag(m, (u'©nam', 'TXXX:TITLE', 'TIT2', 'Title', 'TITLE', 'TRACK TITLE',
                                            'TRACKTITLE', 'TrackTitle', 'Track Title'))

            # Find track number
            track_number = self._get_tag(m, ('TRCK', 'TXXX:TRACK', 'Track', 'trkn', 'TRACK', 'tracknumber', 'TRACKNUMBER'))
            if '/' in track_number:
                track.track = int(track_number.split('/')[0])
            elif track_number:
                track.track = int(track_number)

            # Find disc number
            track_disc = self._get_tag(m, ('TXXX:DISCNUMBER', 'discnumber', 'DISCNUMBER', 'TPOS'))
            if '/' in track_disc:
                track.disc = int(track_disc.split('/')[0])
            elif track_disc:
                track.disc = int(track_disc)

            # Find Genre/Content type
            track.genre = self._get_tag(m, ('TCON', u'@gen', 'gnre', 'Genre', 'genre', 'GENRE', 'TXXX:GENRE'))

            # Find date
            track.date = self._get_tag(m, ('TYER', 'TDAT', 'TDRC', 'TDRL', u'@day', 'date', "DATE", "YEAR", "Date",
                                           "Year", 'TXXX:YEAR'))
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
                artist = get_or_create(s, Artist, name=track_artist, deleted=False)
                track.artist = artist.id
            elif album_artist:
                artist = get_or_create(s, Artist, name=album_artist, deleted=False)
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
                    a_artist = get_or_create(s, Artist, name=album_artist, deleted=False)
                else:
                    a_artist = s.query(Artist).get(1)
                
                # Set album
                try:
                    album = s.query(Album).filter_by(title=album_title, artist=a_artist.id, deleted=False).one()
                    track.album = album.id
                except NoResultFound:
                    album = Album(title=album_title, artist=a_artist.id, cover=1, is_audiobook=is_audiobook)
                    s.add(album)
                    s.commit()
                    track.album = album.id

        # Set dir
        bpath = os.path.dirname(path)
        mdir = get_or_create(s, Directory, directory=bpath, deleted=False)
        track.dir = mdir.id
                 
        # Save everything
        s.add(track)
        s.commit()

        # Check if we need to transcode
        if track.type not in settings.NO_TRANSCODE_FORMATS:
            self.transcode(s, track)

        s.close()

    def transcode(self, s, track):
        at = audiotranscode.AudioTranscode()
        stream = at.transcode_stream(track.file, settings.TRANSCODE_FORMAT)

        cache_file = os.path.join(
            settings.MUSIC_CACHE_DIRECTORY,
            "{}.{}".format(track.id, settings.TRANSCODE_FORMAT))
        with open(cache_file, 'wb') as f:
            maxlen = 0
            for data in stream:
                f.write(data)
                maxlen += len(data)
            track.bytes_tc_len = maxlen
            s.commit()
            log.debug("Transcoded ID %d, result size was %d.", track.id, maxlen)

    def preprocess_deleted(self):
        s = session_get()

        log.debug(u"Removing deleted tracks from database ...")
        for track in s.query(Track).filter_by(deleted=False):
            if not os.path.isfile(track.file):
                self.handle_track_delete(track)
        log.debug(u"Removing deleted covers from database ...")
        for cover in s.query(Cover).filter_by(deleted=False):
            if cover.id == 1:
                continue
            if not os.path.isfile(cover.file):
                self.handle_cover_delete(cover)
        s.close()

    def postprocess_albums(self):
        log.debug(u"Postprocessing albums ...")
        s = session_get()
        found = 0
        for album in s.query(Album).filter_by(deleted=False):
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
        s.close()
        log.debug(u"Found artist for %d new albums", found)
            
    def postprocess_covers(self):
        log.debug(u"Postprocessing covers ...")
        found = 0
        s = session_get()
        for album in s.query(Album).filter_by(deleted=False):
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
                    cover = get_or_create(s, Cover, file=cover_art[0], deleted=False)
                    found += 1

                    # Make thumbnails
                    try:
                        img = Image.open(cover_art[0])
                        size = 200, 200
                        out_file = os.path.join(settings.COVER_CACHE_DIRECTORY, '{}_small.jpg'.format(cover.id))
                        img.thumbnail(size, Image.ANTIALIAS)
                        img.save(out_file, "JPEG")
                    except IOError:
                        log.error(u"Unable to create a small thumbnail for cover ID %d", cover.id)

                    try:
                        img = Image.open(cover_art[0])
                        size = 800, 800
                        out_file = os.path.join(settings.COVER_CACHE_DIRECTORY, '{}_medium.jpg'.format(cover.id))
                        img.thumbnail(size, Image.ANTIALIAS)
                        img.save(out_file, "JPEG")
                    except IOError:
                        log.error(u"Unable to create a medium thumbnail for cover ID %d", cover.id)

                    # Set new cover id for album, and update tracks and the album timestamp for sync
                    s.query(Track).filter_by(album=album.id).update({'updated': utc_now()})
                    s.query(Album).filter_by(id=album.id).update({'updated': utc_now(), 'cover': cover.id})

                    # Cover lookup done for this album, continue with next
                    break

        # That's that, commit changes for this album
        s.commit()
        s.close()
        self._cover_art = {}  # Clear cover art cache
        log.debug(u"Found and attached %d new covers.", found)

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
        s = session_get()
        
        if track.album != 1:
            # If album only has a single (this) track, remove album
            if s.query(Track).filter_by(album=track.album, deleted=False).count() == 0:
                s.query(Album).filter_by(id=track.album, deleted=False).update({'deleted': True, 'updated': utc_now()})
                
        if track.artist != 1:
            # If artist only has a single (this) track, remove artist
            if s.query(Track).filter_by(artist=track.artist, deleted=False).count() == 0:
                s.query(Artist).filter_by(id=track.artist, deleted=False).update({'deleted': True, 'updated': utc_now()})

        # That's that, delete the track.
        s.query(Track).filter_by(id=track.id, deleted=False).update({'deleted': True, 'updated': utc_now()})

        # Save changes
        s.commit()
        s.close()

    def handle_cover_delete(self, cover):
        s = session_get()
        for album in s.query(Album).filter_by(cover=cover.id, deleted=False):
            album.cover = 1
        s.query(Cover).filter_by(id=cover.id, deleted=False).update({'deleted': True, 'updated': utc_now()})
        s.commit()
        s.close()
            
    def handle_delete(self, path):
        track = None
        cover = None
        
        # If it does NOT, make sure it is removed from index
        # First, see if track exists with this path. If not, see if it is a cover.
        # If neither, stop here.
        s = session_get()
        try:
            track = s.query(Track).filter_by(file=path, deleted=False).one()
        except NoResultFound:
            try:
                cover = s.query(Cover).filter_by(file=path, deleted=False).one()
            except NoResultFound:
                return
        s.close()

        # If we found a cover, remove it and clear references to it from albums
        if cover:
            self.handle_cover_delete(cover)
            return

        # If we found a track, remove it from any albums. If the albums are now empty, remove them.
        # If artist does not belong to any track, remove it also
        if track:
            self.handle_track_delete(track)
            return

    def handle_file(self, path, is_audiobook):
        ext = os.path.splitext(path)[1]
        
        if os.path.isfile(path):
            # If file exists, scan it
            if ext in settings.DAEMON_SCAN_FILES:
                self.handle_audio(path, ext, is_audiobook)
            if ext in settings.COVER_EXTENSIONS:
                self.handle_cover(path, ext)
        else:
            self.handle_delete(path)

    def traverse_dir(self, directory, is_audiobook):
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
                    log.debug(u"%d files handled.", self._files)
                self.handle_file(full_path, is_audiobook)

            # Handle subdirs
            for mdir in subdir_list:
                self.traverse_dir(mdir, is_audiobook)

    def process_files(self):
        log.info(u"Scanning directory %s", settings.MUSIC_DIRECTORY)
        self._files = 0
        self._dirs = 0
        self._cover_art = {}
        self.traverse_dir(settings.MUSIC_DIRECTORY, False)
        self.traverse_dir(settings.AUDIOBOOK_DIRECTORY, True)
        log.info(u"Found %d files in %d directories.", self._files, self._dirs)

    def scan_all(self):
        log.info(u"Scanning everything ...")
        self.preprocess_deleted()
        self.process_files()
        self.postprocess_albums()
        self.postprocess_covers()
        self.schedule_scan()
        log.info(u"Scan complete")

    def schedule_scan(self):
        log.info(u"Scheduling a new scan after 30 minutes.")
        self._update_task = task.deferLater(reactor, 1800, self.scan_all)

    def __init__(self):
        self._cover_art = {}  # Save found cover files here
        self._files = 0
        self._dirs = 0
        self._run = True
        self._update_task = None

    def run(self):
        log.info(u"Initial scan ...")
        self.scan_all()
        log.debug(u"Waiting for events ...")
        reactor.run()
        log.debug(u'All done.')

    def stop(self):
        self._run = False
        reactor.stop()
        log.info(u"Quitting ...")




