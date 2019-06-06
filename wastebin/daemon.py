import os
import cherrypy
import logging
import re
from urllib.parse import urlparse
import ZODB
from relstorage.storage import RelStorage
from relstorage.options import Options
from relstorage.adapters.mysql import MySQLAdapter
import persistent
import persistent.list
import ZODB.FileStorage
import persistent.mapping
import BTrees.OOBTree


def pmap():
    return persistent.mapping.PersistentMapping()


class Database(object):
    def __init__(self, storage):
        self.db = ZODB.DB(storage)
        self.init_db()

    @staticmethod
    def from_uri(uri):
        """
        Return a database backed by the storage specified by the passed uri. URIs containing a scheme (scheme://) will
        be checked against installed adapters. Schemeless URIs are assumed to be a file path for flat file storage.
        """
        parsed = urlparse(uri)
        storage = None

        if parsed.scheme:
            mysql = MySQLAdapter(host=parsed.hostname, port=parsed.port,
                                 user=parsed.username, passwd=parsed.password,
                                 db=parsed.path[1:], options=Options(keep_history=False))
            storage = RelStorage(adapter=mysql)
        else:
            storage = ZODB.FileStorage.FileStorage(uri)

        if storage is None:
            raise Exception(f"Unsupported uri {uri}")

        return Database(storage)

    def init_db(self):
        with self.db.transaction() as c:
            if "pastes" not in c.root():
                c.root.pastes = BTrees.OOBTree.BTree()

    def loadpaste(self, name):
        with self.db.transaction() as c:
            return c.root.pastes[name].value

    def writepaste(self, name, contents):
        with self.db.transaction() as c:
            try:
                paste = c.root.pastes[name]
                paste.value = contents
            except KeyError:
                paste = Paste(contents)
                c.root.pastes[name] = paste

    def delpaste(self, name):
        with self.db.transaction() as c:
            del c.root.pastes[name]

    def iterpastes(self, prefix=None):
        with self.db.transaction() as c:
            for name, value in c.root.pastes.items():
                if prefix and not name.startswith(prefix):
                    continue
                yield (name, value, )


class Paste(persistent.Persistent):
    def __init__(self, value):
        self.value = value


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


RE_NAME_RAW = r'^[a-z0-9_\-/]+$'
RE_NAME = re.compile(RE_NAME_RAW)


class WasteWeb(object):
    def __init__(self, db):
        self.db = db

    @cherrypy.expose
    def index(self, load=None):
        data = ""
        if load:
            try:
                data = self.db.loadpaste(load)
            except KeyError:
                raise cherrypy.HTTPError(404)
        yield PAGE.format(data=data.replace("<", "&lt;"), load=load or "")

    @cherrypy.expose
    def make(self, name, contents):
        if not RE_NAME.match(name):
            raise cherrypy.HTTPError(400, f"paste name must match {RE_NAME_RAW}")
        self.db.writepaste(name, contents)
        raise cherrypy.HTTPRedirect("/" + name)

    @cherrypy.expose
    def default(self, *args):
        try:
            if cherrypy.request.method == "DELETE":
                self.db.delpaste(args[0])
                return "OK"
            else:
                cherrypy.response.headers['Content-Type'] = 'text/plain'
                return self.db.loadpaste(args[0]).encode("utf-8")
        except KeyError:
            raise cherrypy.HTTPError(404)

    @cherrypy.expose
    def search(self, prefix=""):
        cherrypy.response.headers['Content-Type'] = 'text/plain'

        def _work():
            for name, _ in self.db.iterpastes(prefix):
                yield name + "\n"
        return _work()


def main():
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="basic pastebin",
                                     epilog="supprted databases are file paths and mysql://")

    parser.add_argument('-p', '--port', default=int(os.environ.get("PASTE_PORT", 8080)), type=int, help="http port")
    parser.add_argument('-d', '--database', default=os.environ.get("PASTE_DB", None), help="database uri")
    parser.add_argument('--debug', action="store_true", help="enable development options")

    args = parser.parse_args()

    if not args.database:
        parser.error("the following arguments are required: -d/--database")

    logging.basicConfig(level=logging.INFO if args.debug else logging.WARNING,
                        format="%(asctime)-15s %(levelname)-8s %(filename)s:%(lineno)d %(message)s")

    web = WasteWeb(Database.from_uri(args.database))

    cherrypy.tree.mount(web, '/', {'/': {'tools.trailing_slash.on': False}})

    cherrypy.config.update({
        "tools.sessions.on": False,
        "server.socket_host": "0.0.0.0",
        "server.socket_port": args.port,
        "server.thread_pool": 5,
        "engine.autoreload.on": args.debug,
        "log.screen": True
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
