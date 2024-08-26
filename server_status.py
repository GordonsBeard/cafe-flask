"""Returns the status of all SRCDS servers defined in servers.cfg"""

import errno
import os
from socket import error as socket_error

from SourceLib.SourceQuery import SourceQuery as SQ  # type: ignore

import caching

SERVERSTATUS_FILENAME = "server_status.cache"  # filename to cache the server data to
SERVERCFG_FILENAME = "servers.cfg"  # filename of the server ip/games
SECONDS_KEPT_FRESH = 120  # number of seconds to keep fresh (2 minutes)


def get_server_status():
    """Returns status dictionary with server info"""
    cache = caching.Cache(SERVERSTATUS_FILENAME, SECONDS_KEPT_FRESH, req_server_info)
    return cache.get()


def req_server_info():
    """Always retrieve as much server information as possible."""
    status_dict = {}

    # Open the server.cfg file up.
    if not os.path.exists(SERVERCFG_FILENAME):
        print("No CFG!")
        return False

    # For each server, loop through status.
    with open(SERVERCFG_FILENAME, encoding="ascii") as serverlist:
        servers = dict(eval(serverlist.read()))  # pylint: disable=eval-used
        for key, value in servers.items():
            ip = value["ip"]
            port = value["port"]
            livestatus = SQ(ip, port)
            try:
                status_dict[key] = livestatus.info()
            except socket_error as serr:
                if serr.errno == errno.ECONNREFUSED:
                    status_dict[key] = {"error": True}
            try:
                status_dict[key] = {}
                status_dict[key]["gamename"] = "Team Fortress 2"
                status_dict[key]["ip"] = ip
                status_dict[key]["port"] = port
                status_dict[key]["players"] = len(livestatus.player())
            except KeyError:
                pass

    return status_dict
