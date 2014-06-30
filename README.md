OverC
=====

OverC (pronounced: oversee): simplistic monitoring solution that is a pleasure to use.

Features:

* Simplicity is the root of all genius: easy to configure and use
* Dynamic and extensible: everything is an extenal plugin
* Agent-less: data is pushed to OverC server

Installation
============

Sending Data
============

OverC uses an extremely simple JSON protocol to report arbitrary monitoring data.

Reporting Services
------------------

OverC does not connect to anything: all data should be POSTed to it as JSON to `/api/set/service/status`:

```json
{
  "server": { "name": "localhost", "key": "1234" },
  "period": 60,
  "services": [
    { "name": "application", "state": "OK", "info": "up 32h" },
    { "name": "cpu", "state": "OK", "info": "28% load" },
    { "name": "queue", "state": "OK", "info": "3 items" },
  ]
}
```

Keys explained:

* `"server"` is the *Server* identification.
  
  Whenever a Server reports for the first time, OverC remembers it and stores its name and access key. 
  Subsequent connections are only authorized if the same server key is used.

* `"period"` is the reporting period in seconds the server promises to keep.
  
  If any of the services do not report within the declared period -- an alert is raised.
  
* `"services"` is the list of *Services* and their current *States*.

    Each Service has a `"name"` which should not be changed.
    
    For each Service, the current State is reported: `"state"` is a string which supports one of the following values:
        
    * `"OK"`: service runs fine
    * `"WARN"`: warning condition
    * `"ERR"`: critical error condition
    * `""`: empty string stands for "unknown", which probably means that its state cannot be retrieved

Note that there's no need to explicitly define Servers and Services: all data is accepted automatically.

Reporting Alerts
----------------

It's possible to send alerts directly by pushing JSON object to `/api/set/alerts`:

```json
{
  "server": { "name": "localhost", "key": "1234" },
  "alerts": [
    { "message": "System down" },
    { "message": "System down" },
    { "message": "Cannot check state for service A", "service": "queue" },
  ]
}
```

If you want to alert about something happened with a particular service, use the "service" key to specify its name.


