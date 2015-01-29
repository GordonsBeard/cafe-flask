""" Cafe of Broken Dreams: the final years """
from server_status import get_server_status
from community import get_group_info

from flask import Flask, render_template

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')

@app.route('/')
def index():
    serverdict  = get_server_status()
    groupinfo   = get_group_info( "cafeofbrokendreams", maxevents=1, maxnews=1 )
    eventdict   = groupinfo["events"]
    newsdict    = groupinfo["announcements"]

    return render_template('index.html', serverinfo = serverdict, eventlist = eventdict, newslist = newsdict)

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')
