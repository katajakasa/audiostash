'use strict';

app.controller('RootController', ['$scope', 'DataService', 'Session', 'sock', 'AUTH_EVENTS', 'AuthService',
  function($scope, DataService, Session, sock, AUTH_EVENTS, AuthService) {
    sock.setHandler("open", function() {
      // Attempt to reconstruct session from localStorage
      if(localStorage.getItem("sid") != null) {
        Session.create(localStorage.getItem("sid"), 0, 0);
        AuthService.authenticate();
      }
    });

    $scope.$on(AUTH_EVENTS.loginSuccess, function(event, args) {
      DataService.start();
    });
    $scope.$on(AUTH_EVENTS.logoutBegin, function(event, args) {
      DataService.stop();
    });

    $scope.is_authenticated = AuthService.is_authenticated;
    $scope.is_authorized = AuthService.is_authorized;
  }
]);

app.controller('NavController', ['$scope', '$location',
  function($scope, $location) {
    $scope.is_active = function(loc) {
        return (loc === $location.path());
    };
  }
]);

app.controller('AuthCheckController', ['$scope', '$location', 'AUTH_EVENTS',
  function($scope, $location, AUTH_EVENTS) {
    $scope.$on(AUTH_EVENTS.loginFailed, function(event, args) {
      $location.path("/login");
    });
    $scope.$on(AUTH_EVENTS.sessionTimeout, function(event, args) {
      $location.path("/login");
    });
  }
]);

app.controller('LoginController', ['$scope', '$rootScope', 'AUTH_EVENTS', 'AuthService',
  function($scope, $rootScope, AUTH_EVENTS, AuthService) {
    $scope.credentials = {
      username: '',
      password: ''
    };
    $scope.login = function(credentials) {
      AuthService.login(credentials);
    };
  }
]);

app.controller('LogoutController', ['$scope', 'AuthService',
  function($scope, AuthService) {
     AuthService.logout();
  }
]);
