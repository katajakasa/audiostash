'use strict';

app.controller('RootCtrl', ['$scope', 'DataService', 'sock',
  function($scope, dbService, sock) {
    sock.setHandler("open", function() {
      AuthService.authenticate();
    });
  }
]);