'use strict';

app.factory('AuthService', ['Session','sock', function(Session, sock) {
  function authenticate() {
  }

  return {
    authenticate: authenticate,
  };
}]);

app.service('Session', function() {
  this.create = function (sessionId, userId, userRole) {
    this.id = sessionId;
    this.userId = userId;
    this.userRole = userRole;
  };
  this.destroy = function () {
    this.id = null;
    this.userId = null;
    this.userRole = null;
  };
});