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

        time.sleep(1)
        self.serial.write("\r\n\r\n")
        time.sleep(2)

        self.serial.write("$H\n")

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

        self.serial.write("$1=255\n")
        self.reset_stepper()

        self.printing = True

    def stop_print(self):

        if not self.is_connected():
            return False

        self.serial.write("\x18\n")
        self.serial.write("$1=25\n")
        self.reset_stepper()

        self.printing = False

    def reset_stepper(self):
        self.serial.write("$X\n")
        self.serial.write("G91\n")
        self.serial.write("G1 Y1 F1000\n")

    def is_connected(self):
        try:
            return self.serial.isOpen()
        except:
            return False

    def wait_for_ok(self):

        msg = ""
        while True:
            msg += self.serial.read(1)
            if "ok" in msg:
                break

    def wait_for_printing_enabled(self):
        while not self.printing or not self.is_connected():
            time.sleep(1)

    def run(self):

        while True:

            self.wait_for_printing_enabled()

            for item in self.playlist:

                item.printing()

                f = open(item.filename, 'r')

                for line in f.readlines():

                    self.wait_for_printing_enabled()
                    print "Writing line...", line
                    self.serial.write(line)
                    print "Done... waiting"
                    self.wait_for_ok()

                print "Item done"
                item.done()

            self.stop_print()
            time.sleep(1)

