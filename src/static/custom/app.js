'use strict';

var app = angular.module(
  'audiostash',
  [
    'ngRoute',
    'indexedDB',
    'bd.sockjs',
    'ui.bootstrap',
    'ui.grid',
  ]
);

app.config(function($indexedDBProvider) {
  $indexedDBProvider
    .connection('audiostash')
    .upgradeDatabase(1, function(event, db, tx) {
      var artist_store        = db.createObjectStore("artist", { keyPath: "pk" });
      var album_store         = db.createObjectStore("album", { keyPath: "pk" });
      var directory_store     = db.createObjectStore("directory", { keyPath: "pk" });
      var playlist_store      = db.createObjectStore("playlist", { keyPath: "pk" });
      var playlisttrack_store = db.createObjectStore("playlisttrack", { keyPath: "pk" });
      var track_store         = db.createObjectStore("track", { keyPath: "pk" });
      var config_store        = db.createObjectStore("config", { keyPath: "pk" });

      album_store.createIndex("artist","artist", { unique: false });
      playlisttrack_store.createIndex("playlist","playlist", { unique: false });
      playlisttrack_store.createIndex("track","track", { unique: false });
      track_store.createIndex("album","album", { unique: false });
      track_store.createIndex("dir","dir", { unique: false });
      track_store.createIndex("artist","artist", { unique: false });
      track_store.createIndex("track", "track", { unique: false });
      track_store.createIndex("disctrack", ['disc','track'], {unique: false});
      config_store.createIndex("key","key", { unique: true });
    });
});

app.factory('sock', function(socketFactory) {
  return socketFactory({
    url: '/sock'
  });
});

app.config(['$routeProvider',
  function($routeProvider) {
    console.log("routes");
    $routeProvider.
      when('/', {
        controller: 'RootCtrl'
      }).
      otherwise({
        redirectTo: '/'
      });
  }
]);

    /*
      when('/login', {
        templateUrl: 'tpl/partials/login.html',
        controller: 'LoginCtrl'
      }).
      when('/front', {
        templateUrl: 'tpl/partials/front.html',
        controller: 'IndexCtrl'
      }).
      when('/albums', {
        templateUrl: 'tpl/partials/albums.html',
        controller: 'AlbumsCtrl'
      }).
      when('/playlists', {
        templateUrl: 'tpl/partials/playlists.html',
        controller: 'PlaylistsCtrl'
      }).*/