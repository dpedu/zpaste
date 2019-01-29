import os
import cherrypy
import logging
import hashlib
import re


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Wastebin</title>
</head>
<body>
    <form action="/make" method="post">
        <textarea name="contents" rows="30" cols="120">{data}</textarea><br />
        <input type="text" name="name" placeholder="url name" value="{load}" /><br />
        <input type="submit" value="Go">
    </form>
</body>
</html>
"""


RE_NAME = re.compile(r'^[a-z0-9_\-/]+$')


def sha256(data):
    h = hashlib.sha256()
    h.update(data.encode("utf-8"))
    return h.hexdigest()


class WasteWeb(object):
    def __init__(self, datadir):
        self.datadir = datadir

    @cherrypy.expose
    def index(self, load=None):
        data = ""
        if load:
            assert RE_NAME.match(load)
            data = self.loadpaste(load)
        yield PAGE.format(data=data.replace("<", "&lt;"), load=load or "")

    @cherrypy.expose
    def make(self, name, contents):
        assert RE_NAME.match(name)
        pname = name or sha256(contents)
        self.writepaste(pname, contents)
        raise cherrypy.HTTPRedirect("/" + pname)

    @cherrypy.expose
    def default(self, *args):
        data = self.loadpaste(args[0])
        yield data

    def loadpaste(self, name):
        path = self.pastepath(sha256(name))
        with open(path) as f:
            f.readline()  # the name
            return f.read()

    def writepaste(self, name, contents):
        hname = sha256(name)
        path = self.pastepath(hname)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(name)
            f.write("\n")
            f.write(contents)

    def pastepath(self, hashedname):
        return os.path.join(self.datadir, hashedname[0], hashedname[1], hashedname + ".txt")


def main():
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="")

    parser.add_argument('-p', '--port', default=8080, type=int, help="http port")
    parser.add_argument('-d', '--data', default="./", help="data dir")
    parser.add_argument('--debug', action="store_true", help="enable development options")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.debug else logging.WARNING,
                        format="%(asctime)-15s %(levelname)-8s %(filename)s:%(lineno)d %(message)s")

    web = WasteWeb(args.data)

    cherrypy.tree.mount(web, '/', {'/': {'tools.trailing_slash.on': False}})

    cherrypy.config.update({
        'tools.sessions.on': False,
        'request.show_tracebacks': True,
        'server.socket_port': args.port,
        'server.thread_pool': 5,
        'server.socket_host': '0.0.0.0',
        'server.show_tracebacks': args.debug,
        'log.screen': False,
        'engine.autoreload.on': args.debug
    })

    def signal_handler(signum, stack):
        logging.critical('Got sig {}, exiting...'.format(signum))
        cherrypy.engine.exit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        cherrypy.engine.start()
        cherrypy.engine.block()
    finally:
        logging.info("API has shut down")
        cherrypy.engine.exit()


if __name__ == '__main__':
    main()
