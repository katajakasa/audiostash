AudioStash
==========

Personal web music/video player with transcoding.

Audiostash can be deployed on a server, pointed to your music collection on local directory, and then used to stream your
music collection over the web to wherever you are (with your hopefully HTML5/mp3 compatible browser :) Also supports
transcoding from other formats to mp3 on-the-fly.

![Audiostash albums view](https://raw.githubusercontent.com/katajakasa/audiostash/master/doc/albums.jpg "Album view with some testdata")

Dependencies
------------

1. Have python2.7, virtualenv, pip and bower installed.
2. For python packages, ```pip install --upgrade -r deploy/requirements.pip```
3. For JS packages, ```bower install```
4. You may also need to have ffmpeg, lame, flac etc. binaries installed.

Installation
------------

1. Copy sec/settings-dist.py to settings.py.
2. Change settings to suit yourself.
3. Set up a virtualenv and install dependencies (see above).
4. Set up database by running ```alembic upgrade head```.
5. ```python -m audiostash.scand.main``` to scan your files to database. After scan is done, close with CTRL+C.
6. ```python -m audiostash.webui.main``` to run the server. Feel free to proxy with nginx or others.
7. Connect with browser to your server to the port you defined in settings.py.
8. Enjoy!

For proxying with nginx, there is a skeleton config file in deploy/audiostasn.nginx
For autostarting with systemd, there are service files in deploy-directory.

License
-------
License is GPLv3. See LICENSE for more details.

Other
-----

Project also contains a copy of python-audiotranscode by Tom Wallroth (https://github.com/devsnd/python-audiotranscode).

Contact
-------
IRC: katajakasa @freenode and @ircnet.
