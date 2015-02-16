# server_status.py
# Author:       Gordon
# Description:  Returns the status of all SRCDS servers defined in servers.cfg
# Last Update:  2/15/2015
import caching
import errno, os
from SourceLib.SourceQuery import SourceQuery as SQ     # SourceLib does all the heavy lifting for us
from socket import error as socket_error

serverstatus_filename = 'server_status.cache'           # filename to cache the server data to
servercfg_filename = 'servers.cfg'                      # filename of the server ip/games
seconds_kept_fresh = 120                                # number of seconds to keep fresh (2 minutes)

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
        servers = dict( eval( serverlist.read() ) )
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
