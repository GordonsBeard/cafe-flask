""" Cafe of Broken Dreams: the final years """

import os.path

from flask import Flask, render_template

from community import get_cache_update_time, get_group_info
from server_status import get_server_status

app = Flask(__name__)


def get_map_images(serverdict):
    """Display the map image for the maps returned by the server"""
    bg_images = {}
    if serverdict is not None:
        for server, details in serverdict.items():
            # Skip this server if it's down
            if not "map" in serverdict[server]:
                bg_images[server] = f"static/img/{server}_default.png"
                continue

            mapfilename = f"static/img/maps/{details['map']}.jpg"
            map_exists = os.path.exists(mapfilename)

            if not map_exists:
                bg_images[server] = f"static/img/{server}_default.png"
            else:
                bg_images[server] = mapfilename
    return bg_images


@app.route("/")
def index():
    """The home page :)"""
    serverdict = get_server_status()
    groupinfo = get_group_info("cafeofbrokendreams", maxevents=3, maxnews=1)
    eventdict = groupinfo["events"]
    newsdict = groupinfo["announcements"]
    updatetime = get_cache_update_time()

    backgrounds = get_map_images(serverdict)

    return render_template(
        "index.html",
        serverinfo=serverdict,
        eventlist=eventdict,
        newslist=newsdict,
        updatetime=updatetime,
        backgrounds=backgrounds,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
