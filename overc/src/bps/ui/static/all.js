(function(){
    var overcApplication = angular.module('overcApplication', ['ngResource']);

    //region Services

    /** API service
     */
    overcApplication.service('api', ['$resource', function($resource){
        this.serverStatus  = $resource(
            'api/status/server/:server_id',
            {server_id: undefined},
            {});
        this.serverAlerts  = $resource(
            'api/status/alerts/server/:server_id',
            {server_id: undefined},
            {
                get: { method: 'GET', params: { hours: 24 } }
            });
        this.serviceAlerts = $resource(
            'api/status/alerts/service_id/:service_id',
            {service_id: undefined},
            {
                get: { method: 'GET', params: { hours: 24 } }
            });
    }]);

    /** Exchange service
     */
    overcApplication.service('X', ['$rootScope', function($rootScope){
        // Create a new scope just for communication
        var $scope = $rootScope.$new();

        this.emit = $scope.$emit.bind($scope);
        this.on = $scope.$on.bind($scope);
    }]);

    //endregion

    //region Controllers

    // TODO: click-selecting servers and services: filter status, alerts
    // TODO: click-load state history for a service
    // TODO: push updates from the server (WOW!)

    /** Services controller
     */
    overcApplication.controller('servicesController', ['$scope', 'api', 'X', function($scope, api, X){
        /** Known servers, services and their states
         * @type {Array}
         */
        $scope.servers = [];

        /** The number of alerts reported today
         * @type {number}
         */
        $scope.n_alerts = 0;

        /** Is the supervisor process running fine?
         * @type {Boolean}
         */
        $scope.supervisor_lag = true;

        // Auto-update servers
        var updateServers = function(){
            api.serverStatus.get(function(res){
                $scope.servers = res.servers;
                $scope.n_alerts = res.n_alerts;
                $scope.supervisor_lag = res.supervisor_lag;
            });
        };
        setInterval(updateServers, 5000);
        updateServers();

        // Auto-update alerts
        $scope.$watch('n_alerts', function(val, oldVal){
            X.emit('update-alerts');
        });
    }]);

    /** Alerts controller
     */
    overcApplication.controller('alertsController', ['$scope', 'api', 'X', function($scope, api, X){
        /** Alerts list
         * @type {Array}
         */
        $scope.alerts = [];

        X.on('update-alerts', _.debounce(function(){
            api.serverAlerts.get(function(res){
                $scope.alerts = res.alerts;
            });
        }, 100));
    }]);

    //endregion
})();
