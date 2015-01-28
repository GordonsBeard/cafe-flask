""" Cafe of Broken Dreams: the final years """
from server_status import get_server_status
from community import get_group_info

from flask import Flask, render_template, redirect, session, json, g, flash
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.openid import OpenID

import re, urllib2
from urllib import urlencode

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')
db = SQLAlchemy(app)
oid = OpenID(app)

_steam_id_re = re.compile('steamcommunity.com/openid/id(.*?)$')

""" User object """
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steam_id = db.Column(db.String(40))
    nickname = db.String(80)

    @staticmethod
    def get_or_create(steam_id):
        rv = User.query.filter_by(steam_id = steam_id).first()
        if rv is None:
            rv = User()
            rv.steam_id = steam_id
            db.session.add(rv)
        return rv

def get_steam_info(steam_id):
    """ Gets the json response from steam's login """
    options = {
        'key': app.config['STEAM_API_KEY'],
        'steamids': steam_id,
    }
    url = 'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0001/?%s' % urlencode(options)
    rv = json.load(urllib2.urlopen(url))
    return rv['response']['players']['player'][0] or {}

@oid.after_login
def create_or_login(resp):
    match = _steam_id_re.search(resp.identity_url)
    g.user = User.get_or_create(match.group(1).strip("/"))
    steamdata = get_steam_info(g.user.steam_id)
    g.user.nickname = steamdata['personaname']
    db.session.commit()
    session['user_id'] = g.user.id
    flash('You are logged in as %s' % g.user.nickname)
    return redirect(oid.get_next_url())

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

@app.route('/login')
@oid.loginhandler
def login():
    if g.user is not None:
        return redirect(oid.get_next_url())
    return oid.try_login('http://steamcommunity.com/openid')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.')
    return redirect(oid.get_next_url())

@app.route('/')
def index():
    serverdict  = get_server_status()
    groupinfo   = get_group_info( "cafeofbrokendreams" )
    eventdict   = groupinfo["events"]
    newsdict    = groupinfo["announcements"]

    # Admin check
    admins = app.config['ADMINS']

    try:
        adminflag = True if g.user.steam_id in admins else False
    except AttributeError:
        adminflag = False

    return render_template('index.html', serverinfo = serverdict, eventlist = eventdict, newslist = newsdict, adminflag = adminflag)

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')
