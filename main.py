import os
import re
from TapConverter import TapConverter
import settings
import sandschreiber
from werkzeug import secure_filename
from flask import Flask, render_template, request, redirect, jsonify

app = Flask(__name__)
app.jinja_env.filters['basename'] = os.path.basename

ss = sandschreiber.AsyncSandschreiber(settings.device, 115200)

def get_gcodes(directory):
    gcodes = []
    for filename in os.listdir(directory):
        filename = os.path.join(directory, filename)

        if os.path.isfile(filename) and filename[-5:] == 'gcode':
            gcodes.append(filename)

    return gcodes

@app.route("/")
def index():
    return render_template('index.jinja2',
        files=get_gcodes(settings.gcode_directory),
        playlist=ss.playlist,
        connected=ss.is_connected(),
        printing=ss.printing,
        sandschreiber=ss
    )

@app.route('/connect', methods=["POST"])
def connect():
    try:
        ss.connect()
        return 'OK'
    except:
        return 'FAIL', 500

@app.route('/disconnect', methods=["POST"])
def disconnect():
    try:
        ss.disconnect()
        return 'OK'
    except:
        return 'FAIL', 500

@app.route('/emergencyStop', methods=["POST"])
def emergency_stop():
    ss.stop_print()
    return 'OK'

@app.route('/upload', methods=["POST"])
def upload_gcode():
    upload_file = request.files['file']
    filename = secure_filename(upload_file.filename)

    if filename.endswith(".tap"):
        filename = re.sub(r'tap$', 'gcode', filename)
        converter = TapConverter(upload_file.read())
        open(os.path.join(settings.gcode_directory, filename), 'w+').write(converter.get_gcode())

    else:
        upload_file.save(os.path.join(settings.gcode_directory, filename))

    return redirect('/', code=301)


@app.route('/upload', methods=["DELETE"])
def upload_delete():
    filename = secure_filename(request.form.get('filename'))
    full_filename = os.path.join(settings.gcode_directory, filename)

    print full_filename

    for item in ss.playlist:
        print item.filename, filename
        if item.filename == full_filename:
            return 'File is in use', 400

    if not os.path.exists(full_filename):
        return 'Filename not found', 404

    os.remove(full_filename)
    return 'OK'


@app.route('/print', methods=["POST"])
def start_print():
    ss.start_print()

    return 'OK'

@app.route('/control', methods=["POST"])
def control():
    command = request.form.get('command')
    if command == 'forward':
        ss.forward()
    elif command == 'backward':
        ss.backward()
    elif command == 'home':
        ss.home()
    elif command == 'pause':
        ss.pause()
    elif command == 'play':
        ss.unpause()
    else:
        return 'Unknown command', 400

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
        pl_item = sandschreiber.PlaylistItem(os.path.join(settings.gcode_directory, filename))
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
    app.run(host=settings.listen, port=settings.port)
