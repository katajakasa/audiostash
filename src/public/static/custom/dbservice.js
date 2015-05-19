'use strict';

app.factory('dbService', ['$indexedDB', 'sock', '$timeout', function($indexedDB, sock, $timeout){
    var svc = null;

    function sync_check_start() {
        console.log("sync_check_start");
        sock.send("Ping");
        sync_init();
    }

    function sync_init() {
        svc = $timeout(function() {
            sync_check_start();
        }, 10000);
    }

    function sync_stop() {
        if(svc != null) {
            $timeout.cancel(svc);
            svc = null;
        }
    }

    return {
        start: sync_init,
        stop: sync_stop,
    }
}]);