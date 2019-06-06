FROM ubuntu:bionic

RUN sed -i -E 's/(archive|security).ubuntu.com/192.168.1.142/' /etc/apt/sources.list && \
    sed -i -E 's/^deb-src/# deb-src/' /etc/apt/sources.list && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
        apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
            wget gpg git build-essential && \
    wget -qO- http://artifact.scc.net.davepedu.com/repo/apt/extpython/dists/bionic/install | bash /dev/stdin && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
        apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
            extpython-python3.7 && \
    apt-get clean autoclean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

ADD . /tmp/code

RUN cd /tmp/code && \
    /opt/extpython/3.7/bin/pip3 install -r requirements.txt && \
    /opt/extpython/3.7/bin/python3 setup.py install && \
    useradd --uid 1000 app

USER app
ENTRYPOINT ["/opt/extpython/3.7/bin/wastebind"]
