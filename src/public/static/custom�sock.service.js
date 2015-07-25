'use strict';

app.factory('SockService', ['sock',
    function(sock){
        var recv_handlers = {};
        var open_handlers = [];

        function setup() {
            sock.setHandler("open", function() {
                for(var i = 0; i < open_handlers.length; i++) {
                    open_handlers[i]();
                }
            });
            sock.setHandler("message", function(data) {
                var msg = angular.fromJson(data['data']);
                var type = msg['type'];
                if(type in recv_handlers) {
                    for(var i = 0; i < recv_handlers[type].length; i++) {
                        recv_handlers[type][i](msg);
                    }
                }
            });
        }

        function add_open_handler(fn) {
            open_handlers.push(fn);
        }

        function add_recv_handler(type, fn) {
            recv_handlers[type] = [];
            recv_handlers[type].push(fn);
        }

        return {
            setup: setup,
            add_open_handler: add_open_handler,
            add_recv_handler: add_recv_handler
        }
    }
]);