OverC
=====

OverC (pronounced: oversee): simplistic monitoring solution that is a pleasure to use.

Features:

* Simplicity is the root of all genius: easy to configure and use
* Dynamic and extensible: everything is a plugin, in any scripting language
* Agent-less: data is pushed to OverC server

<img src="misc/img/overc-server-ui.png" />





Table of Contents
=================

* <a href="#user-content-installation">Installation</a>
    * <a href="#user-content-overclient">Overclient</a>
    * <a href="#user-content-overc-server">OverC Server</a>
        * <a href="#user-content-quickstart-with-docker">Quickstart with Docker</a>
* <a href="#user-content-sending-data">Sending Data</a>
    * <a href="#user-content-json-protocol">JSON Protocol</a>
        * <a href="#user-content-ping">Ping</a>
        * <a href="#user-content-reporting-services">Reporting Services</a>
        * <a href="#user-content-reporting-alerts">Reporting Alerts</a>
    * <a href="#user-content-overcli">Overcli</a>
        * <a href="#user-content-simple-commands">Simple Commands</a>
        * <a href="#user-content-continuous-monitoring">Continuous Monitoring</a>
            * <a href="#user-content-autorun-monitor">Autorun Monitor</a>
* <a href="#user-content-overc-server-1">OverC Server</a>
    * <a href="#user-content-server-installation">Server Installation</a>
        * <a href="#user-content-ubuntu">Ubuntu</a>
    * <a href="#user-content-server-configuration">Server Configuration</a>






Installation
============

Overclient
----------

This tiny app with no dependencies is used to push information to OverC server:

    $ sudo pip install overc
    
OverC Server
------------

Receives information about running services through JSON API, and provides a user interface:

    $ sudo install overc[server]
    
Then you deploy it as a WSGI application, using `overc.wsgi.app` as the entry point. 
Please refer to [Server Intallation](#server-installation) manual.

OverC server uses configuration file in INI format. 
More details are given in [Server Configuration](#server-configuration).

### Quickstart with Docker

If you're lazy to set it up, there's a Docker container ready for you :)

    $ docker start overc-db || docker run --name="overc-db" -d -e MYSQL_ROOT_PASSWORD='root' -e MYSQL_DATABASE='overc' -e MYSQL_USER='overc' -e MYSQL_PASSWORD='overc' -e MYSQL_SET_KEYBUF=32M kolypto/mysql
    $ docker start overc-server || docker run --name="overc-server" -d --link overc-db:db -e OVERC_DB_LINK=DB_PORT_3306 -p 5000:80 -v /etc/overc:/etc/overc kolypto/overc-server
    
Now you have a full-featured OverC server running on port `5000`!

Container description is available in [misc/docker/overc-server](misc/docker/overc-server).




Sending Data
============

JSON Protocol
-------------

OverC uses an extremely simple JSON protocol to report arbitrary monitoring data.
You can use the API as you like, but there also is a [command-line overcli tool](#overcli) available
which offers a complete solution.

In general, the following HTTP codes can be sent in response:

In response, you get one of the following HTTP codes:

* `200`: success
* `400`: malformed request (e.g. not enough data provided)
* `403`: authentication failed (e.g. wrong server key)

### Ping

Checks whether the connection works fine:

```json
{
  "server": { "name": "localhost", "key": "1234" }
}
```

In addition to connection-checking, it also tests server authentication.
Proceed to the next section for more information.

### Reporting Services

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
  
  You can provide any name/key pair for the server identification: the server is automatically registered at OverC.
  Just make sure you keep using the same identification pair: if you try to send a key that's different from the one 
  that was used initially, you'll get an `403 Forbidden` error in response.

* `"period"` is the reporting period in seconds the server promises to keep.
  
  If any of the services do not report within the declared period -- an alert is raised.
  
* `"services"` is the list of *Services* and their current *States*.

    Each Service has a `"name"` which should not be changed.
    
    For each Service, the current State is reported: `"state"` is a string which supports one of the following values:
        
    * `"OK"`: service runs fine
    * `"WARN"`: warning condition
    * `"ERR"`: critical error condition
    * `"UNK"`: unknown, which probably means that its state cannot be retrieved.
    * Any other string is converted to `"UNK"`.
    
    Any additional information can be reported with `"info"`: arbitrary string with runtime data.

    Finally, a different period can be specified per service using the `"period"` key.

Note that there's no need to explicitly define Servers and Services: all data is accepted automatically.

### Reporting Alerts

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

Keys explained:

* `"server"` is the *Server* identification.
* `"alerts"` is the list of alerts you'd like to report
    
    * `"message"`: alert message text
    * `"service"`: (optional) service name to report the alert for, if any.



Overcli
-------

### Simple Commands

OverC comes with a command-line client utility which allows to interact with OverC server.

Two main arguments are:

* `-s`, `--server`: OverC Server URL. Example: `http://localhost:5000/`
* `-i`, `--server-id`: Server identification, `<server-name>:<server-key>`. Example: 'localhost:1234'.
    
      Identification pair is arbitrary, just keep using the same key.

This way, most commands are invoked like this:

    $ overcli -s 'http://localhost:5000' -i 'localhost:1234' <command-name> [arguments...]
    
Example: use `ping` to test the connection:

    $ overcli -s 'http://localhost:5000' -i 'localhost:1234' ping
    
Example: report single service's state:

    $ overcli -s 'http://localhost:5000' -i 'localhost:1234' service-status 60 'app' 'OK' 'Runs fine'
    
Example: report a single alert:

    $ overcli -s 'http://localhost:5000' -i 'localhost:1234' alert "Something bad has happened"

### Continuous Monitoring

The tools described above are just thin wrappers around the HTTP JSON client and are probably not enough for real
monitoring challenges. Using `overcli`, you can set up continuous monitoring for your services using simple scripts.

First, create the configuration file (anywhere):

```ini
[overc]
server=http://user:password@mon.example.com:5000/
my-name=a.example.com
my-key=1234

[service:app]
period=5
command=./plugin.d/app.sh

[service:que]
period=10
command=./plugin.d/que.sh

[service:cpu]
period=10
command=./plugin.d/cpu.sh

[service:echo]
period=5
command=echo 1
```

* Section `[overc]` specifies generic settings:

    * `server`: URL to OverC Server
    * `my-name`, `my-key`: This server identification, name and key.

* Section `[service:<name>]` defines a service to be monitored and reported
    
    * `period` is the time period in seconds defining how often the service status should be reported
    * `command` -- an arbitrary command that tests your service: monitoring plugin.
        
        The command should be a script which prints out the service info, and its return code defines the status:
        
        | Code | Status |
        |------|--------|
        | 0    | OK     |
        | 1    | WARN   |
        | 2    | FAIL   |
        | >= 3 | UNK    |
        
        Any other code is also converted to `"UNK"`.
        
        *NOTE*: This actually follows [Nagios Plugin API](http://nagios.sourceforge.net/docs/3_0/pluginapi.html), so they are reusable! :)

Having this config file, just launch the monitor:

    $ overcli -s 'http://localhost:5000' -i 'localhost:1234' monitor config.ini

All service states will be updated immediately, and continuously monitored ever since.
Any fatal exceptions are reported as alerts to the monitoring server.

For the sake of completeness, here's an example plugin which simply checks whether a process is running:

```bash
#! /usr/bin/env bash
applicaton_name="$1"

# Try to get PID of the running application, or die with code 2 ("FAIL")
application_pid=$(pidof $applicaton_name) || { echo 'Not running!' ; exit 2 }

# Running fine: print PID, exit with 0 ("OK")
echo "PID: $application_pid"
exit 0
```

Then use it like this:

    command=./plugin.d/pid-check.sh "httpd"

#### Autorun Monitor
Okay, we know how to launch the monitor, but we want it to run continuously.

There are multiple ways to do so:

* [Supervisor](http://supervisord.org/).

  If you're already using this awesome process manager,
  just put [this config file](misc/autorun/supervisor/conf.d/overcli-monitor.conf) in `/etc/supervisor/conf.d/`.

* [upstart](http://upstart.ubuntu.com/).

  With Ubuntu, you might like the [upstart script](misc/autorun/init/overcli-monitor.conf): just put it in `/etc/init/`.

  It automatically lists all `/etc/overc/monitor*.ini` files and launch a separate monitoring for each file!





OverC Server
============

Server Installation
-------------------

OverC Server is a WSGI application, and requires a WSGI application server to run. More info:

* [Flask: Starting your app with uwsgi](http://flask.pocoo.org/docs/deploying/uwsgi/)
* [uwsgi: Quickstart for Python/WSGI applications](http://uwsgi-docs.readthedocs.org/en/latest/WSGIquickstart.html)

It requires a MySQL database, make sure you set it up. You don't need to crate any tables: OverC does this for you.

Finally, OverC uses a configuration file in INI format: see [Server Configuration](#server-configuration)

### Ubuntu

Quickstart guide for Ubuntu:

    $ sudo apt-get install nginx-full uwsgi

Put uwsgi application config in `/etc/uwsgi/apps-available/overc.yml`, and symlink it to `/etc/uwsgi/apps-enabled/overc.yml`:
    
```yaml
uwsgi:
  autoload: yes
  plugin: python
  
  uid: www-data
  gid: www-data
  
  chdir: /etc/overc/
  module: overc.wsgi
  callable: app
```

Then, configure nginx to `/etc/nginx/sites-available/overc.conf`, and symlink it to `/etc/nginx/sites-enabled/overc.conf`:

```
upstream overc {
    server unix:///var/run/uwsgi/app/overc/socket;
}

server {
    listen 80;
    server_name localhost;

    root /var/www;

    access_log /var/log/nginx/overc.access.log combined;
    error_log  /var/log/nginx/overc.error.log;

    # Statics
    location /ui/static {
        alias /usr/local/lib/python2.7/dist-packages/overc/src/bps/ui/static;
    }

    location / {
        include uwsgi_params;
        uwsgi_pass overc;
    }
}
```

And restart services:

    $ sudo service nginx restart
    $ sudo service uwsgi restart

OverC requires a MySQL database to run, so make sure you set it up as well:

    $ sudo apt-get install mysql-server mysql-client
    $ echo "CREATE DATABASE IF NOT EXISTS \`overc\` CHARACTER SET utf8 COLLATE utf8_general_ci;" | mysql
    $ echo "GRANT ALL ON \`overc\`.* to 'overc'@'%' IDENTIFIED BY 'overc';" | mysql



Server Configuration
--------------------

