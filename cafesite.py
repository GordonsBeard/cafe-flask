""" Cafe of Broken Dreams: the final years """
import os.path
from server_status import get_server_status
from community import get_group_info, get_cache_update_time

from flask import Flask, render_template

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')

def get_map_images(serverdict):
    bg_images = {}
    for server, details in serverdict.items():
        # Skip this server if it's down
        if not serverdict[server].has_key( 'map' ) :
            continue

        mapfilename = 'static/img/maps/{0}.jpg'.format(serverdict[server]['map'])
        map_exists = os.path.exists( mapfilename )

        if not map_exists:
            bg_images[server] = 'static/img/{0}_default.png'.format(server)
        else:
            bg_images[server] = mapfilename

    return bg_images

@app.route('/')
def index():
    serverdict  = get_server_status()
    groupinfo   = get_group_info( "cafeofbrokendreams", maxevents=3, maxnews=1 )
    eventdict   = groupinfo["events"]
    newsdict    = groupinfo["announcements"]
    updatetime  = get_cache_update_time()

    backgrounds = get_map_images(serverdict)

    return render_template('index.html', serverinfo = serverdict, eventlist = eventdict, newslist = newsdict, updatetime = updatetime, backgrounds = backgrounds)

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')
