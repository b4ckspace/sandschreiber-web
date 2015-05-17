import os
import glob
import sandschreiber
from werkzeug import secure_filename
from flask import Flask, render_template, request, redirect, jsonify

app = Flask(__name__)
app.jinja_env.filters['basename'] = os.path.basename

GCODE_DIRECTORY='gcodes'

ss = sandschreiber.AsyncSandschreiber('/dev/ttyUSB0', 115200)

@app.route("/")
def index():
    return render_template('index.jinja2',
        files=glob.glob(GCODE_DIRECTORY + u'/*.gcode'),
        playlist=ss.playlist,
        connected=ss.is_connected(),
        printing=ss.printing
    )

@app.route('/connect', methods=["POST"])
def connect():
    ss.connect()
    return 'OK'

@app.route('/disconnect', methods=["POST"])
def disconnect():
    ss.disconnect()
    return 'OK'

@app.route('/emergencyStop', methods=["POST"])
def emergency_stop():
    ss.stop_print()
    return 'OK'

@app.route('/upload', methods=["POST"])
def upload_gcode():
    upload_file = request.files['file']
    filename = secure_filename(upload_file.filename)

    upload_file.save(os.path.join(GCODE_DIRECTORY, filename))

    return redirect('/', code=301)

@app.route('/print', methods=["POST"])
def start_print():
    ss.start_print()

    return 'OK'

@app.route('/print', methods=["DELETE"])
def stop_print():
    ss.stop_print()
    ss.playlist.clear()

    return 'OK'

@app.route("/playlist", methods=["GET"])
def playlist_get():
    return jsonify(playlist=ss.playlist.as_json())

@app.route('/playlist', methods=["POST"])
def playlist_add():

    filename = request.form.get('filename')
    if filename:
        filenames = [filename]
    else:
        filenames = request.form.getlist('filename[]')

    for filename in filenames:
        pl_item = sandschreiber.PlaylistItem(os.path.join(GCODE_DIRECTORY, filename))
        ss.playlist.add(pl_item)

    return 'OK'

@app.route('/playlist', methods=["DELETE"])
def playlist_remove():
    index = request.form.get('index')
    if index:
        ss.playlist.remove(int(index))
    else:
        ss.playlist.clear()

    return 'OK'

if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0')
