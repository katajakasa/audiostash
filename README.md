AudioStash
==========

Personal web music/video player with transcoding.

Audiostash can be deployed on a server, pointed to your music collection on local directory, and then used to stream your
music collection over the web to wherever you are (with your hopefully HTML5/mp3 compatible browser :) Also supports
transcoding from other formats to mp3 on-the-fly.

![Audiostash albums view](https://raw.githubusercontent.com/katajakasa/audiostash/master/doc/albums.jpg "Album view with some testdata")

Dependencies
------------

```pip install --upgrade -r deploy/requirements.pip```

You also need to have ffmpeg binary installed.

Installation
------------

1. Copy sec/settings-dist.py to settings.py.
2. Change settings to suit yourself.
3. Set up a virtualenv and install dependencies (see above).
4. ```python scand.py``` to scan your files to database. After scan is done, close with CTRL+C.
5. ```python audiostash.py``` to run the server. Feel free to proxy with nginx or others.
6. Connect with browser to your server to the port you defined in settings.py.
7. Enjoy!

For proxying with nginx, there is a skeleton config file in 
deploy/audiostasn.nginx
For autostarting with systemd, there are service files in deploy/audiostash-scand.service and deploy/audiostash-webui.service.

License
-------
License is GPLv3. See LICENSE for more details.

Other
-----

Project also contains a copy of python-audiotranscode by Tom Wallroth (https://github.com/devsnd/python-audiotranscode).

Contact
-------
IRC: katajakasa @freenode and @ircnet.
