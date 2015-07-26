'use strict';

app.factory('DataService', ['$indexedDB', 'sock', '$timeout', 'SockService',
    function($indexedDB, sock, $timeout, SockService){
        var svc = null;
        var sync_ts = -1;
        var sync_list = [];

        // Hot data request happens
        //
        // sync_check_start() -> Send table status request to server
        // sync_event() -> receiver response from server
        // sync_status_response() -> called by sync_event, gets status response and updates syncable tables list
        // sync_data_fetch(( -> If there are syncable tables, previous calls this. Sends request for data.
        // sync_request_response()

        function sync_check_start() {
            console.log("sync_check_start");
            sock.send(angular.toJson({
                'type': 'sync',
                'message': {
                    'query': 'status',
                    'ts': localStorage['last_sync']
                }
            }));
        }

        function sync_data_fetch() {
            console.log("sync_data_fetch");

            // If there is nothing more to sync, stop here.
            if(sync_list.length == 0) {
                sync_check_finished();
                return;
            }

            // Request for data for the first table in the array
            sock.send(angular.toJson({
                'type': 'sync',
                'message': {
                    'query': 'request',
                    'ts': localStorage['last_sync'],
                    'table': sync_list.shift()
                }
            }));
        }

        function sync_status_response(data) {
            sync_list = data['status'];
            sync_ts = data['ts'];
            if(sync_list.length == 0) {
                sync_check_finished();
            } else {
                sync_data_fetch();
            }
        }

        function sync_request_response(msg) {
            var data = msg['data'];
            var table = msg['table'];

            $indexedDB.openStore(table, function(store) {
                for(var i = 0; i < data.length; i++) {
                    store.upsert(data[i]);
                }
            });
            sync_data_fetch();
        }

        function sync_event(msg) {
            var data = msg['data'];
            if(data['query'] == 'status') {
                sync_status_response(data);
            } else if(data['query'] == 'request') {
                sync_request_response(data);
            }
        }

        function sync_check_finished() {
            localStorage['last_sync'] = sync_ts;
            schedule_next_sync();
        }

        function reset_localstorage() {
            if(localStorage.getItem("initialized") == null) {
                localStorage['last_sync'] = "2000-01-01T00:00:00Z";
                localStorage['initialized'] = 1;
            }
        }

        function schedule_next_sync() {
            svc = $timeout(function() {
                sync_check_start();
            }, 10000);
        }

        function sync_init() {
            reset_localstorage();
            sync_check_start();
        }

        function sync_stop() {
            if(svc != null) {
                $timeout.cancel(svc);
                svc = null;
            }
        }

        function setup() {
            SockService.add_recv_handler('sync', sync_event);
        }

        return {
            setup: setup,
            start: sync_init,
            stop: sync_stop
        }
    }
]);