# Using LTS ubuntu
FROM ubuntu:14.04
MAINTAINER "Mark Vartanyan <kolypto@gmail.com>"

# Packages: update & install
ENV DEBCONF_FRONTEND noninteractive
RUN apt-get update -qq
RUN apt-get install -qq -y --no-install-recommends python-pip python-dev build-essential supervisor
RUN apt-get install -qq -y --no-install-recommends libmysqlclient-dev libpcre3 libpcre3-dev
RUN apt-get install -qq -y --no-install-recommends nginx-full apache2-utils
RUN pip install uwsgi j2cli


# Install OverC server
RUN pip install   overc[server]

# Put files
ADD conf /root/conf

# Configure uwsgi
RUN mkdir /etc/uwsgi
ADD conf/uwsgi-overc.yml /etc/uwsgi/overc.yml

# Configure nginx
RUN echo "daemon off;" >> /etc/nginx/nginx.conf
RUN rm /etc/nginx/sites-enabled/default
RUN nginx -t

# Configure supervisor
ADD conf/supervisor-all.conf /etc/supervisor/conf.d/

# Configure OverC
ADD conf/overc /etc/overc
RUN mkdir /var/run/overc && chown www-data:www-data /var/run/overc


# Runner
ADD run.sh /root/run.sh



# Declare
VOLUME ["/etc/overc"]
EXPOSE 80

CMD ["/root/run.sh"]
