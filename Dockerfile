FROM ubuntu:bionic

RUN apt-get update && \
    apt-get install -y python3-pip

ADD . /tmp/code/

RUN pip3 install -U pip && \
    cd /tmp/code && \
    python3 setup.py install && \
    useradd --uid 1000 app

VOLUME /data/
USER app
ENTRYPOINT ["wastebind", "-d", "/data/"]
