"""
    Module used to return the status of all Cafe servers.
"""

from SourceLib.SourceQuery import SourceQuery as SQ
import errno, os, pickle, datetime
from socket import error as socket_error

serverstatus_filename = 'server_statuses'
servercfg_filename = 'servers.cfg'
seconds_kept_fresh = 120

def modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)

def get_server_status():
    """ Returns status dictionary with server info """
    # Open the status file.
    # If it doesn't exist, create it with fresh data.
    if not os.path.exists(serverstatus_filename):
        statusfile = open(serverstatus_filename, 'w')
        status = req_server_info()
        pickle.dump(status, statusfile)
        statusfile.close()

    # Check if it needs updating.
    rightnow = datetime.datetime.now()
    statusmtime = modification_date(serverstatus_filename)
    twominutes = datetime.timedelta(0,  seconds_kept_fresh, 0)

    if (rightnow - statusmtime) > twominutes:
        # If it does, get new data.
        return req_server_info()
    else:
        # Otherwise return the old smell stale data.
        statusfile = open(serverstatus_filename, 'r')
        status = pickle.load(statusfile)
        return status

def req_server_info():
    """ Always retrieve as much server information as possible. """
    status_dict = {}

    # Open the server.cfg file up.
    if not os.path.exists(servercfg_filename):
        print "No CFG! Create one you dumbass!"
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

    # Write stuff to pickle file
    statusfile = open(serverstatus_filename, 'w')
    pickle.dump(status_dict, statusfile)
    statusfile.close()

    return status_dict
