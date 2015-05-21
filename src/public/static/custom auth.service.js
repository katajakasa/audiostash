'use strict';

app.factory('AuthService', ['$location', '$rootScope', 'Session', 'sock', 'AUTH_EVENTS',
  function($location, $rootScope, Session, sock, AUTH_EVENTS) {
    function auth_event(data) {
      sock.removeHandler('message');
      if(data['type'] != 'message') {
        return;
      }
      var msg = angular.fromJson(data['data']);
      if(msg['type'] == "auth" && msg['error'] == 0) {
        Session.create(
          msg['data']['sid'],
          msg['data']['uid'],
          msg['data']['level']
        );
        $rootScope.$broadcast(AUTH_EVENTS.loginSuccess);
        console.log("Login success!");
      } else {
        $rootScope.$broadcast(AUTH_EVENTS.sessionTimeout);
        console.error("Session timeout!");
      }
    }

    function authenticate() {
      sock.setHandler('message', auth_event);
      sock.send(angular.toJson({
        'type': 'auth',
        'message': {
          'sid': Session.sid,
        }
      }));
    }

    function login_event(data) {
      sock.removeHandler('message');
      if(data['type'] != 'message') {
        return;
      }
      var msg = angular.fromJson(data['data']);
      if(msg['type'] == "login" && msg['error'] == 0) {
        Session.create(
          msg['data']['sid'],
          msg['data']['uid'],
          msg['data']['level']
        );
        $rootScope.$broadcast(AUTH_EVENTS.loginSuccess);
        $location.path('/dashboard');
      } else {
        $rootScope.$broadcast(AUTH_EVENTS.loginFailed);
        console.error("Login error!");
      }
    }

    function login(credentials) {
      sock.setHandler('message', login_event);
      sock.send(angular.toJson({
        'type': 'login',
        'message': {
          'username': credentials.username,
          'password': credentials.password,
        }
      }));
    }

    function logout() {
      $rootScope.$broadcast(AUTH_EVENTS.logoutBegin);
      sock.send(angular.toJson({
        'type': 'logout',
        'message': {}
      }));
      Session.destroy();
      $rootScope.$broadcast(AUTH_EVENTS.logoutSuccess);
    }

    function is_authenticated() {
      return !!Session.uid;
    }

    function is_authorized(req_level) {
      return (is_authenticated() && req_level >= Session.level);
    }

    return {
      authenticate: authenticate,
      login: login,
      logout: logout,
      is_authorized: is_authorized,
      is_authenticated: is_authenticated,
    };
  }
]);

app.service('Session', [
  function() {
    this.create = function(sid, uid, level) {
      this.sid = sid;
      this.uid = uid;
      this.level = level;
      localStorage['sid'] = sid;
    };
    this.destroy = function() {
      this.sid = '';
      this.uid = null;
      this.level = 0;
      localStorage.removeItem('sid');
    };
  }
]);