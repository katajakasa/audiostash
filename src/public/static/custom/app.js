'use strict';

var app = angular.module(
    'audiostash',
    [
        'ngRoute',
        'indexedDB',
        'ng.sockjs',
        'ui.bootstrap',
        'ui.grid'
    ]
);

app.config(function ($indexedDBProvider) {
    $indexedDBProvider
        .connection('audiostash')
        .upgradeDatabase(1, function (event, db, tx) {
            var artist_store = db.createObjectStore("artist", {keyPath: "id"});
            var album_store = db.createObjectStore("album", {keyPath: "id"});
            var directory_store = db.createObjectStore("directory", {keyPath: "id"});
            var playlist_store = db.createObjectStore("playlist", {keyPath: "id"});
            var playlisttrack_store = db.createObjectStore("playlisttrack", {keyPath: "id"});
            var track_store = db.createObjectStore("track", {keyPath: "id"});
            var config_store = db.createObjectStore("config", {keyPath: "id"});

            album_store.createIndex("artist", "artist.id", {unique: false});
            album_store.createIndex("is_audiobook", "is_audiobook", {unique: false});
            playlisttrack_store.createIndex("playlist", "playlist", {unique: false});
            playlisttrack_store.createIndex("track", "track", {unique: false});
            track_store.createIndex("album_id", "album_id", {unique: false});
            track_store.createIndex("dir", "dir", {unique: false});
            track_store.createIndex("artist_id", "artist_id", {unique: false});
            track_store.createIndex("track", "track", {unique: false});
            track_store.createIndex("disctrack", ['disc', 'track'], {unique: false});
            config_store.createIndex("key", "key", {unique: true});
        }).upgradeDatabase(2, function (event, db, tx) {
            var track_store = event.currentTarget.transaction.objectStore("track");
            track_store.createIndex("is_audiobook", "album.is_audiobook", {unique: false});
        });
});

// Sockjs
app.value('ngSockRetry', 5000);
app.value('ngSockUrl', '/sock');

// URLs
// (custom) requireLogin: True for logincheck
app.config(['$routeProvider',
    function ($routeProvider) {
        $routeProvider.
            when('/login', {
                templateUrl: '/partials/login.html',
                controller: 'LoginController'
            }).
            when('/logout', {
                templateUrl: '/partials/logout.html',
                controller: 'LogoutController'
            }).
            when('/albums', {
                templateUrl: '/partials/albums.html',
                controller: 'AlbumsController',
                requireLogin: true
            }).
            when('/album/:artistId/:albumId', {
                templateUrl: '/partials/album.html',
                controller: 'AlbumController',
                requireLogin: true
            }).
            when('/tracks', {
                templateUrl: '/partials/tracks.html',
                controller: 'AlbumTrackController',
                requireLogin: true
            }).
            when('/audiobooks', {
                templateUrl: '/partials/audiobooks.html',
                controller: 'AudiobooksController',
                requireLogin: true
            }).
            when('/playlists', {
                templateUrl: '/partials/playlists.html',
                requireLogin: true
            }).
            otherwise({
                redirectTo: '/login'
            });
    }
]);
