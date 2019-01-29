FROM ubuntu:bionic

ADD . /tmp/code/

RUN apt-get update && \
    apt-get install -y python3-pip

RUN pip3 install -U pip && \
    cd /tmp/code && \
    python3 setup.py install && \
    useradd --uid 1000 app

VOLUME /data/

ENTRYPOINT ["wastebind", "-d", "/data/"]
