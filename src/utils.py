# -*- coding: utf-8 -*-

import settings
import sys
import getpass
from passlib.hash import pbkdf2_sha256
from common.tables import USERLEVELS, database_init, session_get, User

def create_admin(_username, _password):
    database_init(settings.DBFILE)
    pw_hash = pbkdf2_sha256.encrypt(_password)
    s = session_get()
    user = User(username=_username, password=pw_hash, level=USERLEVELS['admin'])
    s.add(user)
    s.commit()
    print("User '{}' created.".format(username))

if 'create_admin' in sys.argv:
    username = raw_input("Username: ")
    password = getpass.getpass()
    create_admin(username, password)
    exit(0)

print("AudioStash utilities")
print("create_admin - Creates a new admin user")
exit(0)
