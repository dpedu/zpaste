from appdirs import user_config_dir
import os
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
    spr_action.add_parser("list", help="show list of pastes")

    spr_new = spr_action.add_parser("new", help="create a paste")
    spr_new.add_argument("name", nargs="?", default="", help="name of paste to create")

    spr_get = spr_action.add_parser("get", help="get a paste")
    spr_get.add_argument("name", help="name of paste to get")

    spr_edit = spr_action.add_parser("edit", help="edit a paste")
    spr_edit.add_argument("name", help="name of paste to edit")

    spr_del = spr_action.add_parser("del", help="delete a paste")
    spr_del.add_argument("name", help="name of paste to delete")

    args = parser.parse_args()
    r = requests.session()

    host = args.host.rstrip("/") + "/"

    def getpaste(name):
        req = r.get(host + name)
        req.raise_for_status()
        return req.text

    def putpaste(name, body):
        return r.post(host + "make", data={"name": name, "contents": body})

    if args.action in ("new", "edit", "get"):
        if args.action in ("edit", "get"):
            content = getpaste(args.name)
        if args.action == "get":
            print(content, end="")
            return
        with tempfile.NamedTemporaryFile() as f:
            if args.action == "edit":
                f.write(content.encode("utf-8"))
                f.flush()
            content = editor(f.name)
        if not content:
            print("Blank paste, exiting")
        r = putpaste(args.name, content)
        r.raise_for_status()
        print(r.url)

    elif args.action == "del":
        r.delete(host + args.name).raise_for_status()

    elif args.action == "list":
        print(r.get(host + "search").text, end="") 

if __name__ == "__main__":
    main()
