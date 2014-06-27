# Using LTS ubuntu
FROM ubuntu:14.04
MAINTAINER "Mark Vartanyan <kolypto@gmail.com>"

# Packages: update & install
ENV DEBCONF_FRONTEND noninteractive
RUN apt-get update -qq
RUN apt-get install -qq -y --no-install-recommends python-pip supervisor build-essential


# Runner
ADD run.sh /root/run.sh



# Declare
VOLUME ["/etc/nagios/", "/usr/local/nagios/var/"]
EXPOSE 80
EXPOSE 5666
EXPOSE 5667

CMD ["/root/run.sh"]

