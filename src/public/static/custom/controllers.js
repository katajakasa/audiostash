'use strict';

app.controller('RootCtrl', ['$scope', 'dbService', 'sock',
  function($scope, dbService, sock) {
    sock.setHandler("open", function() {
      dbService.start();
    });
  }
]);