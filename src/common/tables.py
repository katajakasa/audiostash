# -*- coding: utf-8 -*-

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

USERLEVELS = {
    'none': 0,
    'user': 1,
    'admin': 2,
}


class Artist(Base):
    __tablename__ = "artist"
    id = Column(Integer, primary_key=True)
    name = Column(String(128))
    updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name
        }


class Cover(Base):
    __tablename__ = "cover"
    id = Column(Integer, primary_key=True)
    file = Column(String(255))
    updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class Album(Base):
    __tablename__ = "album"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=True)
    artist = Column(ForeignKey('artist.id'))
    cover = Column(ForeignKey('cover.id'))
    updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'artist': session_get().query(Artist).filter_by(id=self.artist).one().serialize(),
            'cover': self.cover
        }


class Directory(Base):
    __tablename__ = "directory"
    id = Column(Integer, primary_key=True)
    directory = Column(String(255), nullable=True)
    updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def serialize(self):
        return {
            'id': self.id,
            'directory': self.directory
        }


class Playlist(Base):
    __tablename__ = "playlist"
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name
        }


class PlaylistItem(Base):
    __tablename__ = "playlistitem"
    id = Column(Integer, primary_key=True)
    track = Column(ForeignKey('track.id'))
    number = Column(Integer)
    updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def serialize(self):
        return {
            'id': self.id,
            'track': self.track,
            'number': self.number
        }


class Track(Base):
    __tablename__ = "track"
    id = Column(Integer, primary_key=True)
    file = Column(String(255))
    type = Column(String(8))
    bytes_len = Column(Integer)
    bytes_tc_len = Column(Integer)
    updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    album = Column(ForeignKey('album.id'))
    dir = Column(ForeignKey('directory.id'))
    artist = Column(ForeignKey('artist.id'))
    title = Column(String(128))
    track = Column(Integer)
    disc = Column(Integer)
    date = Column(String(16))
    comment = Column(Text)

    def serialize(self):
        return {
            'id': self.id,
            'album': session_get().query(Album).filter_by(id=self.album).one().serialize(),
            'album_id': self.album,
            'dir': self.dir,
            'artist': session_get().query(Artist).filter_by(id=self.artist).one().serialize(),
            'artist_id': self.artist,
            'title': self.title,
            'track': self.track,
            'disc': self.disc,
            'date': self.date,
            'comment': self.comment
        }


class Setting(Base):
    __tablename__ = "setting"
    id = Column(Integer, primary_key=True)
    key = Column(String(32))
    value = Column(Text)
    updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def serialize(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value
        }


class Log(Base):
    __tablename__ = "log"
    id = Column(Integer, primary_key=True)
    entry = Column(Text)
    updated = Column(DateTime(timezone=True), default=func.now())

    def serialize(self):
        return {
            'id': self.id,
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
    start = Column(DateTime(timezone=True), default=func.now())


_session = sessionmaker()


def database_init(dbfile):
    engine = create_engine('sqlite:///{}'.format(dbfile))
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
        s.add(album)
        s.add(artist)
        s.commit()
