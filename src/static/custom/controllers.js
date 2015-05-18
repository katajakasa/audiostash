'use strict';

app.controller('RootCtrl', ['$scope', '$indexedDB', 'sock',
  function($scope, $indexedDB, sock) {
    console.log("Ctrl");
    sock.setHandler("open", function() {
      console.log("Sock open!");
      sock.send("test!");
    });


    /*
      $scope.objects = [];

      $indexedDB.openStore('album', function(store) {
        store.getAll().then(function(album) {
          $scope.objects = album;
        });
      });

      $scope.load = function() {

      }
    */
  }
]);