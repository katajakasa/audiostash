'use strict';

app.factory('AuthService', ['$location', '$rootScope', 'Session', 'sock', 'AUTH_EVENTS', 'SockService',
  function($location, $rootScope, Session, sock, AUTH_EVENTS, SockService) {
    function auth_event(msg) {
      if(msg['error'] == 0) {
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
      sock.send(angular.toJson({
        'type': 'auth',
        'message': {
          'sid': Session.sid
        }
      }));
    }

    function login_event(msg) {
      if(msg['error'] == 0) {
        Session.create(
          msg['data']['sid'],
          msg['data']['uid'],
          msg['data']['level']
        );
        $rootScope.$broadcast(AUTH_EVENTS.loginSuccess);
        $location.path('/albums');
      } else {
        $rootScope.$broadcast(AUTH_EVENTS.loginFailed);
        console.error("Login error!");
      }
    }

    function login(credentials) {
      sock.send(angular.toJson({
        'type': 'login',
        'message': {
          'username': credentials.username,
          'password': credentials.password
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

    function setup() {
      SockService.add_recv_handler('auth', auth_event);
      SockService.add_recv_handler('login', login_event);
    }

    return {
      setup: setup,
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