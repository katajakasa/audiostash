AudioStash
==========

Personal web music/video player with transcoding.

Requirements
------------

```pip install --upgrade -r deploy/requirements.txt```

You also need to have ffmpeg binary installed.

Installation
------------

1. Copy sec/settings-dist.py to settings.py.
2. Change settings to suit yourself.
3. Install dependencies (see above).
4. ```python scand.py``` to scan your files to database. After scan is done, close with CTRL+C.
5. ```python audiostash.py``` to run the server. Feel free to proxy with nginx or others.
6. Connect with browser to your server to the port you defined in settings.py.
7. Enjoy!

License
-------
License is GPLv3. See LICENSE for more details.

Other
-----

Project also contains a copy of python-audiotranscode by Tom Wallroth (https://github.com/devsnd/python-audiotranscode).

Contact
-------
IRC: katajakasa @freenode and @ircnet.
