'use strict';

app.run(['$rootScope', '$location', 'AuthService', 'DataService', 'SockService', 'PlaylistService', 'Session', 'AUTH_EVENTS',
    function ($rootScope, $location, AuthService, DataService, SockService, PlaylistService, Session, AUTH_EVENTS) {

        // Make sure we are logged in the next page requires that
        $rootScope.$on('$routeChangeStart', function (event, next, current) {
            if (AuthService.is_authenticated() && next.originalPath == '/login') {
                event.preventDefault();
                $location.path('/albums');
            }
        });

        // If we hear and event about login failing, just redirect back to /login page
        $rootScope.$on(AUTH_EVENTS.loginFailed, function (event, args) {
            $location.path("/login");
        });

        // ... Same with session timing out
        $rootScope.$on(AUTH_EVENTS.sessionTimeout, function (event, args) {
            $location.path("/login");
        });

        // If login is done, start up the dataservice for database syncs
        $rootScope.$on(AUTH_EVENTS.loginSuccess, function (event, args) {
            DataService.start();
        });

        // If logout is started, stop running the database sync service
        $rootScope.$on(AUTH_EVENTS.logoutBegin, function (event, args) {
            DataService.stop();
            window.sm2BarPlayers[0].actions.stop();
        });

        // Add a listener for our websocket/sockjs socket opening.
        SockService.add_open_handler(function () {
            // Attempt to reconstruct session from localStorage
            if (localStorage.getItem("sid") != null) {
                Session.create(localStorage.getItem("sid"), 0, 0);
                AuthService.authenticate();
            }
        });

        soundManager.setup({
            url: '/static/lib/soundmanagerv297a/swf/'
        });

        // Initialize our services
        AuthService.setup();
        SockService.setup();
        DataService.setup();
        PlaylistService.setup();

        $rootScope.session_id = AuthService.session_id;
    }
]);

app.controller('AlbumsController', ['$scope', '$rootScope', '$indexedDB', '$location', 'SYNC_EVENTS',
    function ($scope, $rootScope, $indexedDB, $location, SYNC_EVENTS) {
        $scope.albums = [];

        function refresh() {
            $indexedDB.openStore('album', function (store) {
                store.eachWhere(store.query().$index('is_audiobook').$eq(0)).then(function (albums) {
                    $scope.albums = albums;
                });
            });
        }

        $scope.redirect_album = function (artist_id, album_id) {
            $location.path('/album/' + artist_id + '/' + album_id)
        };

        // Automatically refresh on new data
        $rootScope.$on(SYNC_EVENTS.newData, function (event, args) {
            refresh();
        });

        refresh();
    }
]);

app.controller('AudiobooksController', ['$scope', '$rootScope', '$indexedDB', '$location', 'SYNC_EVENTS',
    function ($scope, $rootScope, $indexedDB, $location, SYNC_EVENTS) {
        $scope.albums = [];

        function refresh() {
            $indexedDB.openStore('album', function (store) {
                store.eachWhere(store.query().$index('is_audiobook').$eq(1)).then(function (albums) {
                    $scope.albums = albums;
                });
            });
        }

        $scope.redirect_album = function (artist_id, album_id) {
            $location.path('/album/' + artist_id + '/' + album_id)
        };

        // Automatically refresh on new data
        $rootScope.$on(SYNC_EVENTS.newData, function (event, args) {
            refresh();
        });

        refresh();
    }
]);

app.controller('PlaylistController', ['$scope', '$window', 'PlaylistService', 'PLAYLIST_EVENTS', 'AuthService',
    function ($scope, $window, PlaylistService, PLAYLIST_EVENTS, AuthService) {
        $scope.playlist = [];
        $scope.$on(PLAYLIST_EVENTS.refresh, function (event, args) {
            $scope.playlist = PlaylistService.get_list();
            $window.sm2BarPlayers[0].playlistController.refresh();
            console.log("Updated.");
        });

        $scope.del_song = function (track_id) {
            PlaylistService.del(track_id);
            if (!PlaylistService.has_data()) {
                $window.sm2BarPlayers[0].actions.stop();
            }
        };

        $scope.is_visible = function () {
            return AuthService.is_authenticated();
        };

        $scope.playlist = PlaylistService.get_list();
    }
]);

app.controller('PlayerController', ['$scope', 'AuthService', 'PlaylistService',
    function ($scope, AuthService, PlaylistService) {
        $scope.is_visible = function () {
            return (AuthService.is_authenticated() && PlaylistService.has_data());
        }
    }
]);

app.controller('TrackController', ['$scope', '$indexedDB', '$location', '$routeParams', 'PlaylistService',
    function ($scope, $indexedDB, $location, $routeParams, PlaylistService) {
        $scope.$scope = $scope;
        $scope.artist = null;
        $scope.album = null;
        $scope.grid_opts = {
            enableSorting: true,
            enableHorizontalScrollbar: 0,
            enableVerticalScrollbar: 0,
            enableGridMenu: false,
            rowHeight: 30,
            columnDefs: [
                {
                    name: "add",
                    displayName: "",
                    width: 30,
                    enableColumnMenu: false,
                    cellTemplate: '<div><span ng-click="grid.appScope.add_song(row.entity)" class="song_add track_icon glyphicon glyphicon-plus-sign"></span></div>'
                },
                {name: 'Title', field: 'title'},
                {name: 'Artist', field: 'artist.name'},
                {name: 'Album', field: 'album.title'},
                {name: 'Date', field: 'date', width: 70, enableColumnMenu: false},
                {name: 'Genre', field: 'genre', width: 100, enableColumnMenu: false},
                {name: 'T#', field: 'track', width: 50, enableColumnMenu: false},
                {name: 'D#', field: 'disc', width: 50, enableColumnMenu: false}
            ]
        };

        $scope.add_song = function (track) {
            PlaylistService.add(track.id);
        };

        function refresh() {
            $indexedDB.openStore('track', function (store) {
                store.getAll().then(function (tracks) {
                    $scope.grid_opts.minRowsToShow = tracks.length;
                    $scope.grid_opts.virtualizationThreshold = tracks.length;
                    $scope.grid_opts.data = tracks;
                });
            });
        }

        refresh();
    }
]);

app.controller('AlbumController', ['$scope', '$indexedDB', '$location', '$routeParams', 'PlaylistService',
    function ($scope, $indexedDB, $location, $routeParams, PlaylistService) {
        $scope.$scope = $scope;
        $scope.artist = null;
        $scope.album = null;
        $scope.grid_opts = {
            enableSorting: true,
            enableHorizontalScrollbar: 0,
            enableVerticalScrollbar: 0,
            enableGridMenu: false,
            rowHeight: 30,
            columnDefs: [
                {
                    name: "add",
                    displayName: "",
                    width: 30,
                    enableColumnMenu: false,
                    cellTemplate: '<div><span ng-click="grid.appScope.add_song(row.entity)" class="song_add track_icon glyphicon glyphicon-plus-sign"></span></div>'
                },
                {name: 'Title', field: 'title', enableColumnMenu: false},
                {name: 'Date', field: 'date', width: 70, enableColumnMenu: false},
                {name: 'Genre', field: 'genre', width: 100, enableColumnMenu: false},
                {name: 'T#', field: 'track', width: 50, enableColumnMenu: false},
                {name: 'D#', field: 'disc', width: 50, enableColumnMenu: false}
            ]
        };

        $scope.add_song = function (track) {
            PlaylistService.add(track.id);
        };

        $scope.replace = function (album_id) {
            console.log("Replace playlist");
            PlaylistService.clear();
            $scope.queue(album_id);
        };

        $scope.queue = function (album_id) {
            console.log("Queue to playlist");
            $indexedDB.openStore('track', function (store) {
                store.eachWhere(store.query().$index('album_id').$eq(album_id)).then(function (tracks) {
                    PlaylistService.add_tracks(tracks);
                });
            });
        };

        function refresh() {
            var album_id = parseInt($routeParams.albumId);
            var artist_id = parseInt($routeParams.artistId);

            $indexedDB.openStore('album', function (store) {
                store.find(album_id).then(function (album) {
                    $scope.album = album;
                });
            });
            $indexedDB.openStore('artist', function (store) {
                store.find(artist_id).then(function (artist) {
                    $scope.artist = artist;
                });
            });
            $indexedDB.openStore('track', function (store) {
                store.eachWhere(store.query().$index('album_id').$eq(album_id)).then(function (tracks) {
                    $scope.grid_opts.minRowsToShow = tracks.length;
                    $scope.grid_opts.virtualizationThreshold = tracks.length;
                    $scope.grid_opts.data = tracks;
                });
            });
        }

        refresh();
    }
]);

app.controller('NavController', ['$scope', '$location', 'AuthService',
    function ($scope, $location, AuthService) {
        $scope.sites = [
            {url: '/albums', name: 'Albums', requireLogin: true},
            {url: '/audiobooks', name: 'Audiobooks', requireLogin: true},
            {url: '/tracks', name: 'Tracks', requireLogin: true},
            {url: '/login', name: 'Login', requireLogin: false},
            {url: '/logout', name: 'Logout', requireLogin: true}
        ];

        $scope.is_active = function (loc) {
            return (loc === $location.path());
        };
        $scope.is_visible = function (url) {
            for (var i = 0; i < $scope.sites.length; i++) {
                if ($scope.sites[i].url == url) {
                    if ($scope.sites[i].requireLogin) {
                        return (AuthService.is_authenticated());
                    } else {
                        return (!AuthService.is_authenticated());
                    }
                }
            }
            return true;
        }
    }
]);

app.controller('LoginController', ['$scope', '$location', '$rootScope', 'AUTH_EVENTS', 'AuthService',
    function ($scope, $location, $rootScope, AUTH_EVENTS, AuthService) {
        $scope.error = "";

        $scope.credentials = {
            username: '',
            password: ''
        };

        $scope.login = function (credentials) {
            AuthService.login(credentials);
        };

        $scope.$on(AUTH_EVENTS.loginSuccess, function (event, args) {
            $location.path('/albums');
        });
        $scope.$on(AUTH_EVENTS.loginFailed, function (event, args) {
            $scope.error = AuthService.get_last_error();
        });
    }
]);

app.controller('LogoutController', ['$scope', 'AuthService',
    function ($scope, AuthService) {
        AuthService.logout();
    }
]);
