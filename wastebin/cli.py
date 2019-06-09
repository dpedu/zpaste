from appdirs import user_config_dir
import os
import sys
import json
import argparse
import requests
import tempfile
import subprocess


APPNAME = "wpaste"
CONFDIR = user_config_dir(APPNAME)
CONFPATH = os.path.join(CONFDIR, "conf.json")


def editor(fpath):
    """
    Open the editor
    """
    subprocess.check_call([os.environ["EDITOR"], fpath])  # XXX commented for testing
    with open(fpath) as f:
        content = f.read()
        return content


def main():
    conf = {"host": "", "username": "", "password": ""}
    if os.path.exists(CONFPATH):
        with open(CONFPATH) as cf:
            conf = json.load(cf)
    else:
        os.makedirs(CONFDIR, exist_ok=True)
        with open(CONFPATH, "w") as cf:
            json.dump(conf, cf)

    parser = argparse.ArgumentParser(description="Wastebin cli",
                                     epilog="host/username/password will be saved to {} "
                                            "after first use.".format(CONFPATH))

    parser.add_argument("--host", default=conf["host"], help="http/s host to connect to")
    # parser.add_argument("-u", "--username", help="username")
    # parser.add_argument("-p", "--password", help="password")

    spr_action = parser.add_subparsers(dest="action", help="action to take")

    spr_list = spr_action.add_parser("list", help="show list of pastes")
    spr_list.add_argument("name", nargs="?", help="prefix to match")

    spr_new = spr_action.add_parser("new", help="create a paste")
    spr_new.add_argument("-i", "--stdin", action="store_true", help="read contents from stdin")
    spr_new.add_argument("name", help="name of paste to create")

    spr_get = spr_action.add_parser("get", help="get a paste")
    spr_get.add_argument("name", help="name of paste to get")

    spr_edit = spr_action.add_parser("edit", help="edit a paste")
    spr_edit.add_argument("-i", "--stdin", action="store_true", help="read contents from stdin")
    spr_edit.add_argument("name", help="name of paste to edit")

    spr_del = spr_action.add_parser("del", help="delete a paste")
    spr_del.add_argument("name", help="name of paste to delete")

    # batch operations
    spr_batch = spr_action.add_parser("batch", help="batch operations")
    spr_batch_action = spr_batch.add_subparsers(dest="batchaction", help="action to take")

    spr_import = spr_batch_action.add_parser("import", help="import many text files to pastes")
    spr_import.add_argument("files", nargs="+", help="name of paste to get")

    spr_export = spr_batch_action.add_parser("export", help="export pastes to many text files")
    spr_export.add_argument("dir", help="directory to write files")

    args = parser.parse_args()
    sess = requests.session()

    host = args.host.rstrip("/") + "/"

    def getpaste(name):
        req = sess.get(host + name)
        req.raise_for_status()
        return req.text

    def putpaste(name, body):
        return sess.post(host + "make", data={"name": name, "contents": body})

    if args.action == "get":
        print(getpaste(args.name), end="")

    elif args.action in ("new", "edit"):
        if args.stdin:
            content = sys.stdin.read()
        else:
            with tempfile.NamedTemporaryFile() as f:
                if args.action == "edit":
                    f.write(getpaste(args.name).encode("utf-8"))
                    f.flush()
                content = editor(f.name)
        if not content:
            print("Blank paste, exiting")
        r = putpaste(args.name, content)
        r.raise_for_status()
        print(r.url)

    elif args.action == "del":
        sess.delete(host + args.name).raise_for_status()

    elif args.action == "list":
        print(sess.get(host + "search",
                       params={"prefix": args.name} if args.name else None).text,
              end="")

    elif args.action == "batch":
        if args.batchaction == "import":
            for fpath in args.files:
                pastename = os.path.basename(fpath)
                if pastename.endswith(".txt"):
                    pastename = pastename[0:-4]
                with open(fpath) as f:
                    content = f.read()
                r = putpaste(pastename, content)
                r.raise_for_status()
                print(r.url)
        elif args.batchaction == "export":
            os.makedirs(args.dir, exist_ok=True)
            for name in sess.get(host + "search").text.split("\n"):
                if not name:
                    continue
                outfile = os.path.join(args.dir, f"{name}.txt")
                with open(outfile, "w") as f:  # TODO validate name doesnt have slashes and whatnot
                    f.write(getpaste(name))
                print(outfile)
        else:
            parser.error('must specify an action')
    else:
        parser.error('must specify an action')


if __name__ == "__main__":
    main()
