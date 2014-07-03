OverC Server
============

Contains:

* OverC server
* uwsgi
* nginx

Exports
-------

* nginx on `80`
* `/etc/overc`: configuration

Variables
---------

* `OVERC_DB_NAME=overc`: Database name to work on
* `OVERC_DB_USER=overc`: MySQL user
* `OVERC_DB_PASS=overc`: MySQL password
* `OVERC_DB_HOST=localhost`: MySQL host to connect to
* `OVERC_DB_PORT=3306`: MySQL port

* `OVERC_API_AUTH=`: API authentication: "username:password". Optional.
* `OVERC_UI_AUTH=`: UI authentication: "username:password". Optional.

Linking:

* `OVERC_DB_LINK=`: Database link name. Example: a value of "DB_PORT_3306" will fill in `OVERC_DB_HOST/PORT` variables

Examples
--------

Run MySQL database, OverC server:

    $ docker start overc-db || docker run --name="overc-db" -d -e MYSQL_ROOT_PASSWORD='root' -e MYSQL_DATABASE='overc' -e MYSQL_USER='overc' -e MYSQL_PASSWORD='overc' -e MYSQL_SET_KEYBUF=32M kolypto/mysql

    $ docker start overc-server || docker run --name="overc-server" -d --link overc-db:db -e OVERC_DB_LINK=DB_PORT_3306 -p 80:80 kolypto/overc-server
