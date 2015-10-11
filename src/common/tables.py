# -*- coding: utf-8 -*-

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from common.utils import utc_now

Base = declarative_base()

USERLEVELS = {
    'none': 0,
    'user': 1,
    'admin': 2,
}


class SyncMixin(object):
    deleted = Column(Boolean, default=False)
    updated = Column(DateTime(timezone=True), default=utc_now(), onupdate=utc_now())


class Artist(Base, SyncMixin):
    __tablename__ = "artist"
    id = Column(Integer, primary_key=True)
    name = Column(String(128))

    def serialize(self):
        return {
            'id': self.id,
            'deleted': self.deleted,
            'name': self.name
        }


class Cover(Base, SyncMixin):
    __tablename__ = "cover"
    id = Column(Integer, primary_key=True)
    file = Column(String(255))

    def serialize(self):
        return {
            'id': self.id,
            'deleted': self.deleted,
            'file': self.file
        }


class Album(Base, SyncMixin):
    __tablename__ = "album"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=True)
    artist = Column(ForeignKey('artist.id'))
    cover = Column(ForeignKey('cover.id'))
    is_audiobook = Column(Boolean, default=False)

    def serialize(self):
        return {
            'id': self.id,
            'deleted': self.deleted,
            'title': self.title,
            'is_audiobook': 1 if self.is_audiobook else 0,
            'artist': session_get().query(Artist).filter_by(id=self.artist, deleted=False).one().serialize(),
            'cover': self.cover
        }


class Directory(Base, SyncMixin):
    __tablename__ = "directory"
    id = Column(Integer, primary_key=True)
    directory = Column(String(255), nullable=True)

    def serialize(self):
        return {
            'id': self.id,
            'deleted': self.deleted,
            'directory': self.directory
        }


class Playlist(Base, SyncMixin):
    __tablename__ = "playlist"
    id = Column(Integer, primary_key=True)
    name = Column(String(64))

    def serialize(self):
        return {
            'id': self.id,
            'deleted': self.deleted,
            'name': self.name
        }


class PlaylistItem(Base, SyncMixin):
    __tablename__ = "playlistitem"
    id = Column(Integer, primary_key=True)
    track = Column(ForeignKey('track.id'))
    playlist = Column(ForeignKey('playlist.id'))
    number = Column(Integer)

    def serialize(self):
        return {
            'id': self.id,
            'deleted': self.deleted,
            'playlist': self.playlist,
            'track': session_get().query(Track).filter_by(id=self.track, deleted=False).one().serialize(),
            'track_id': self.track,
            'number': self.number
        }


class Track(Base, SyncMixin):
    __tablename__ = "track"
    id = Column(Integer, primary_key=True)
    file = Column(String(255))
    type = Column(String(8))
    bytes_len = Column(Integer)
    bytes_tc_len = Column(Integer)
    album = Column(ForeignKey('album.id'))
    dir = Column(ForeignKey('directory.id'))
    artist = Column(ForeignKey('artist.id'))
    title = Column(String(128))
    track = Column(Integer)
    disc = Column(Integer)
    date = Column(String(16))
    genre = Column(String(32))
    comment = Column(Text)

    def serialize(self):
        return {
            'id': self.id,
            'deleted': self.deleted,
            'album': session_get().query(Album).filter_by(id=self.album, deleted=False).one().serialize(),
            'album_id': self.album,
            'dir': self.dir,
            'artist': session_get().query(Artist).filter_by(id=self.artist, deleted=False).one().serialize(),
            'artist_id': self.artist,
            'title': self.title,
            'track': self.track,
            'disc': self.disc,
            'date': self.date,
            'genre': self.genre,
            'comment': self.comment
        }


class Setting(Base, SyncMixin):
    __tablename__ = "setting"
    id = Column(Integer, primary_key=True)
    key = Column(String(32))
    value = Column(Text)

    def serialize(self):
        return {
            'id': self.id,
            'deleted': self.deleted,
            'key': self.key,
            'value': self.value
        }


class Log(Base, SyncMixin):
    __tablename__ = "log"
    id = Column(Integer, primary_key=True)
    entry = Column(Text)

    def serialize(self):
        return {
            'id': self.id,
            'deleted': self.deleted,
            'entry': self.entry
        }


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True)
    password = Column(String(255))
    level = Column(Integer, default=USERLEVELS['none'])


class Session(Base):
    __tablename__ = "session"
    key = Column(String(32), primary_key=True)
    user = Column(ForeignKey('user.id'))
    start = Column(DateTime(timezone=True), default=utc_now())


_session = sessionmaker()


def database_init(engine_str):
    engine = create_engine(engine_str)
    _session.configure(bind=engine)
    Base.metadata.create_all(engine)
    database_ensure_initial()


def session_get():
    return _session()


def database_ensure_initial():
    s = session_get()

    if s.query(Album).count() == 0:
        cover = Cover(id=1, file="")
        artist = Artist(id=1, name="Unknown")
        album = Album(id=1, title="Unknown", artist=1, cover=1)
        s.add(cover)
        s.add(artist)
        s.commit()
        s.add(album)
        s.commit()

    if s.query(Playlist).count() == 0:
        playlist = Playlist(id=1, name="Scratchpad")
        s.add(playlist)
        s.commit()
