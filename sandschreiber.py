import threading
import serial
import time

class PlaylistItem(object):

    STATUS_IDLE = 'warten'
    STATUS_DONE = 'fertig'
    STATUS_PRINTING = 'druckt...'

    def __init__(self, filename):
        self.filename = filename
        self.status = self.STATUS_IDLE

    def printing(self):
        self.status = self.STATUS_PRINTING

    def done(self):
        self.status = self.STATUS_DONE

    def idle(self):
        self.status = self.STATUS_IDLE

    def as_json(self):
        return {
            'filename': self.filename,
            'status': self.status
        }


class Playlist(object):

    def __init__(self):
        self.playlist = []
        self.idx = 0

    def add(self, playlist_item):
        self.playlist.append(playlist_item)

    def remove(self, index):
        del self.playlist[index]

    def reset(self):
        for item in self.playlist:
            item.idle()

    def clear(self):
        self.playlist = []

    def __iter__(self):
        self.idx = 0
        return self

    def __len__(self):
        return len(self.playlist)

    def __getitem__(self, index):
        return self.playlist[index]

    def next(self):

        if self.idx >= len(self.playlist):
            raise StopIteration

        self.idx += 1
        return self.playlist[self.idx - 1]

    def as_json(self):
        return [item.as_json() for item in self.playlist]


class AsyncSandschreiber(threading.Thread):

    def __init__(self, device, baud):
        super(AsyncSandschreiber, self).__init__()

        self.playlist = Playlist()
        self.printing = False

        self.device = device
        self.baud = baud

        self.serial = False

        self.setDaemon(True)
        self.start()

    def connect(self):

        self.playlist.reset()
        self.serial = serial.Serial(port=self.device, baudrate=self.baud, timeout=0.1)

        if not self.is_connected():
            self.serial.open()

#        time.sleep(1)
#        self.serial.write("\r\n\r\n")
        time.sleep(2)

        self.home()

    def disconnect(self):
        if self.serial:
            self.serial.close()

    def reconnect(self):
        if self.is_connected():
            self.disconnect()

        self.connect()

    def start_print(self):

        if not self.is_connected():
            return False

        self.unlock_grlb()
        self.write_blocking("$1=255\n")
        self.write_blocking("G90\n")

        self.printing = True

    def home(self):
        self.unlock_grlb()
        self.write("$H\n")

    def forward(self):
        self.unlock_grlb()
        self.write("G91\n")
        self.write("G1 X50 F5000\n")

    def backward(self):
        self.unlock_grlb()
        self.write("G91\n")
        self.write("G1 X-50 F5000\n")

    def unlock_grlb(self):
        self.write_blocking("$X\n")

    def stop_print(self):

        if not self.is_connected():
            return False

        self.write("\x18\n")
        self.write("$1=25\n")

        self.printing = False

    def reset_stepper(self):
        self.write_blocking("$X\n")
        self.write_blocking("G90\n")
        self.write_blocking("G1 Y1 F1000\n")

    def write(self, cmd):
        print "W:", cmd
        self.serial.write(cmd)

    def read(self, bytes):
        result = self.serial.read(bytes)
        print "R:", result
        return result

    def is_connected(self):
        try:
            return self.serial.isOpen()
        except:
            return False

    def wait_for_ok(self):

        msg = ""
        while True:
            msg += self.read(1)
            if "ok" in msg:
                break

    def write_blocking(self, cmd):
        self.write(cmd)
        self.wait_for_ok()

    def wait_for_printing_enabled(self):
        while not self.printing or not self.is_connected():
            time.sleep(1)

    def run(self):

        while True:

            self.wait_for_printing_enabled()

            i = 0
            while i < len(self.playlist):
                item = self.playlist[i]
                item.printing()

                f = open(item.filename, 'r')
                for line in f.readlines():
                    self.write_blocking(line)

                print "Item done"
                item.done()

                i += 1

            self.printing = False
            time.sleep(1)

