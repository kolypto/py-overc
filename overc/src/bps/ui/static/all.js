$(function(){
    var overcApplication = angular.module('overcApplication', []);



    /** Services controller
     */
    overcApplication.controller('servicesController', ['$scope', function($scope){
        /** Known services and their states
         * @type {Array}
         */
        $scope.services = [];
    }]);

    /** Alerts controller
     */
    overcApplication.controller('alertsController', ['$scope', function($scope){

    }]);
});
