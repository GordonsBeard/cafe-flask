"""
    Module used to return the status of all Cafe servers.
"""

from SourceLib.SourceQuery import SourceQuery as SQ
import errno, os, pickle, datetime
from socket import error as socket_error

import caching

serverstatus_filename = 'server_status.cache'
servercfg_filename = 'servers.cfg'
seconds_kept_fresh = 120

def get_server_status():
    """ Returns status dictionary with server info """
    cache = caching.Cache( serverstatus_filename, seconds_kept_fresh, req_server_info )
    return cache.get( )

def req_server_info():
    """ Always retrieve as much server information as possible. """
    status_dict = {}

    # Open the server.cfg file up.
    if not os.path.exists(servercfg_filename):
        print "No CFG!"
        return False


    # For each server, loop through status.
    with open(servercfg_filename) as serverlist:
        servers = eval(serverlist.read())
        for server in servers.keys():
            ip = servers[server]['ip']
            port = servers[server]['port']
            livestatus = SQ(ip, port)
            try:
                status_dict[server] = livestatus.info()
            except socket_error as serr:
                if serr.errno == errno.ECONNREFUSED:
                    status_dict[server] = {'error': True}
            try:
                status_dict[server]['gamename'] = servers[server]['name']
                status_dict[server]['ip'] = ip
                status_dict[server]['port'] = port
            except KeyError:
                pass

    return status_dict
