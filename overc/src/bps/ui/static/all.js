(function(){
    var overcApplication = angular.module('overcApplication', []);

    //region Services

    /** API service
     */
    overcApplication.service('api', ['$http', function($http){
        /** Load servers status
         */
        this.loadServers = function(callback){
            $http({method: 'GET', url: 'api/status/server'})
                .success(function(data, status, headers, config) {
                    callback(undefined, data);
                })
                .error(function(data, status, headers, config) {
                    callback(status);
                });
        };
    }]);

    //endregion

    /** Services controller
     */
    overcApplication.controller('servicesController', ['$scope', 'api', function($scope, api){
        /** Known servers, services and their states
         * @type {Array}
         */
        $scope.servers = [];

        // Auto-update
        var updateServers = function(){
            api.loadServers(function(e, response){
                $scope.servers = response.servers;
            });
        };
        setInterval(updateServers, 10000);
        updateServers();
    }]);

    /** Alerts controller
     */
    overcApplication.controller('alertsController', ['$scope', 'api', function($scope, api){

    }]);
})();
