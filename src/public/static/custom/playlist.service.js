'use strict';

app.factory('PlaylistService', ['$rootScope', '$indexedDB', 'PLAYLIST_EVENTS',
  function($rootScope, $indexedDB, PLAYLIST_EVENTS) {
    var playlist = [];

    function add(track_id) {
      $indexedDB.openStore('track', function(store) {
        store.find(track_id).then(function(track) {
          playlist.push({
            artist: track.artist.name,
            title: track.title,
            id: track.id,
            url: '/track/'+track.id+'.mp3'
          });
          $rootScope.$broadcast(PLAYLIST_EVENTS.refresh);
          save();
        });
      });
    }

    function del(track_id) {
        for(var i = 0; i < playlist.length; i++) {
            if(playlist[i].id == track_id) {
                playlist.splice(i, 1);
                $rootScope.$broadcast(PLAYLIST_EVENTS.refresh);
                save();
                return;
            }
        }
    }

    function save() {
        localStorage['playlist'] = angular.toJson(playlist);
    }

    function load() {
        var jsonlist = localStorage.getItem('playlist');
        if(jsonlist != null && jsonlist != "") {
            playlist = angular.fromJson(jsonlist);
            $rootScope.$broadcast(PLAYLIST_EVENTS.refresh);
        }
    }

    function get_list() {
        return playlist;
    }

    function has_data() {
        return (playlist.length > 0);
    }

    return {
      add: add,
      del: del,
      get_list: get_list,
      has_data: has_data,
      setup: load
    };
  }
]);