""" Cafe of Broken Dreams: the final years """
from server_status import get_server_status
from community import get_group_info, get_cache_update_time

from flask import Flask, render_template

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')

@app.route('/')
def index():
    serverdict  = get_server_status()
    groupinfo   = get_group_info( "cafeofbrokendreams", maxevents=1, maxnews=1 )
    eventdict   = groupinfo["events"]
    newsdict    = groupinfo["announcements"]
    updatetime  = get_cache_update_time()

    return render_template('index.html', serverinfo = serverdict, eventlist = eventdict, newslist = newsdict, updatetime = updatetime)

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')
