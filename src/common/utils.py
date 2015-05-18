# -*- coding: utf-8 -*-

import sys
import re

""" Attempt to decode path with correct encoding """
def decode_path(name):
    return name.decode(sys.getfilesystemencoding())

track_matcher_1 = re.compile('([0-9]+)[\s|_]?-[\s|_]?(.*)[\s|_]?-[\s|_]?(.*)')
track_matcher_2 = re.compile('([0-9]+)[\s|_][\s|_]?(.*)')
track_matcher_3 = re.compile('(.*)[\s|_]?-[\s|_]?(.*)')

""" Attempt to detect title and artist from song filename """
def match_track_filename(filename):
    m = track_matcher_1.match(filename)
    if m:
        return m.group(2), m.group(3)

    m = track_matcher_2.match(filename)
    if m:
        return None, m.group(2)

    m = track_matcher_3.match(filename)
    if m:
        return m.group(1), m.group(2)

    return None, None

""" Gets an instance if it exists, or creates a new one if not. """
def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance
