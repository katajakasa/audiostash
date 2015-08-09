'use strict';

app.factory('PlaylistService', ['$rootScope', '$indexedDB', 'SockService', 'PLAYLIST_EVENTS',
    function ($rootScope, $indexedDB, SockService, PLAYLIST_EVENTS) {
        var playlist = [];

        function add(track_id) {
            $indexedDB.openStore('track', function (store) {
                store.find(track_id).then(function (track) {
                    add_track(track);
                });
            });
        }

        function add_tracks(tracks) {
            for (var i = 0; i < tracks.length; i++) {
                _add_track(tracks[i]);
            }
            save();
            $rootScope.$broadcast(PLAYLIST_EVENTS.refresh);
        }

        function add_track(track) {
            _add_track(track);
            save();
            $rootScope.$broadcast(PLAYLIST_EVENTS.refresh);
        }

        function _add_track(track) {
            playlist.push({
                artist: track.artist.name,
                title: track.title,
                id: track.id
            });
        }

        function del(track_id) {
            for (var i = 0; i < playlist.length; i++) {
                if (playlist[i].id == track_id) {
                    playlist.splice(i, 1);
                    save();
                    $rootScope.$broadcast(PLAYLIST_EVENTS.refresh);
                    return;
                }
            }
        }

        function clear() {
            playlist = [];
            save();
        }

        function save() {
            SockService.send({
                'type': 'playlist',
                'message': {
                    'query': 'save_playlist',
                    'id': 1,
                    'tracks': playlist
                }
            });
        }

        function load() {
            load_playlist(1);
        }

        function get_list() {
            return playlist;
        }

        function has_data() {
            return (playlist.length > 0);
        }

        function create_playlist(name) {
            SockService.send({
                'type': 'playlist',
                'message': {
                    'query': 'add_playlist',
                    'name': name
                }
            });
        }

        function delete_playlist(id) {
            SockService.send({
                'type': 'playlist',
                'message': {
                    'query': 'del_playlist',
                    'id': id
                }
            });
        }

        function copy_scratchpad(id) {
            SockService.send({
                'type': 'playlist',
                'message': {
                    'query': 'copy_scratchpad',
                    'id': id
                }
            });
        }

        function load_playlist(id) {
            playlist = [];
            $indexedDB.openStore('playlistitem', function (store) {
                store.eachWhere(store.query().$index('playlist').$eq(id)).then(function(entries) {
                    for(var i = 0; i < entries.length; i++) {
                        _add_track(entries[i].track);
                    }
                    $rootScope.$broadcast(PLAYLIST_EVENTS.refresh);
                });
            });
        }

        return {
            add: add,
            del: del,
            get_list: get_list,
            has_data: has_data,
            setup: load,
            clear: clear,
            add_track: add_track,
            add_tracks: add_tracks,
            create_playlist: create_playlist,
            delete_playlist: delete_playlist,
            load_playlist: load_playlist,
            copy_scratchpad: copy_scratchpad
        };
    }
]);