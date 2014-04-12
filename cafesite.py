""" Cafe of Broken Dreams: the final years """

from server_status import get_server_status

from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def index():
    serverdict = get_server_status()
    return render_template('index.html', serverinfo = serverdict)

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')
