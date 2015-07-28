'use strict';

app.constant('AUTH_EVENTS', {
  loginSuccess: 'auth-login-success',
  loginFailed: 'auth-login-failed',
  logoutBegin: 'auth-logout-begin',
  logoutSuccess: 'auth-logout-success',
  sessionTimeout: 'auth-session-timeout',
  notAuthenticated: 'auth-not-authenticated',
  notAuthorized: 'auth-not-authorized'
});

app.constant('PLAYLIST_EVENTS', {
  refresh: 'playlist-refresh'
});

app.constant('SYNC_EVENTS', {
  started: 'sync-started',
  stopped: 'sync-stopped',
  newData: 'sync-newdata'
});

app.constant('USERLEVELS', [
  'none',
  'user',
  'admin'
]);