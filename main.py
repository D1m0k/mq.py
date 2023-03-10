import re
import threading
import time

import pystrix


def _demo_handler(agi, args, kwargs, match, path):
    """
    `agi` is the AGI instance used to process events related to the channel, `args` is a
    collection of positional arguments provided with the script as a tuple, `kwargs` is a
    dictionary of keyword arguments supplied with the script (values are enumerated in a list),
    `match` is the regex match object (None if the fallback handler), and `path` is the string
    path supplied by Asterisk, in case special processing is needed.

    The directives issued in this function can all raise Hangup exceptions, which should be
    caught if doing anything complex, but an uncaught exception will simply cause a warning to
    be raised, making AGI scripts very easy to write.
    """
    agi.execute(pystrix.agi.core.Answer())  # Answer the call
    print('its demo')
    response = agi.execute(pystrix.agi.core.StreamFile('demo-thanks', escape_digits=(
    '1', '2')))  # Play a file; allow DTMF '1' or '2' to interrupt
    if response:  # Playback was interrupted; if you don't care, you don't need to catch this
        (dtmf_character, offset) = response  # The key pressed by the user and the playback time

    agi.execute(pystrix.agi.core.Hangup())  # Hang up the call
    
    
def _noop_handler(agi, args, kwargs, match, path):
    """
    Does nothing, causing control to return to Asterisk's dialplan immediately; provided just
    to demonstrate the fallback handler.
    """
    print('its noop')


class FastAGIServer(threading.Thread):
    """
    A simple thread that runs a FastAGI server forever.
    """
    _fagi_server = None  # The FastAGI server controlled by this thread

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

        self._fagi_server = pystrix.agi.FastAGIServer(port=4573,interface='0.0.0.0')

        self._fagi_server.register_script_handler(re.compile('demo'), _demo_handler)
        self._fagi_server.register_script_handler(None, _noop_handler)
        print(self._fagi_server._script_handlers)
        print(f'Server is UP on port {self._fagi_server.socket}')

    def kill(self):
        self._fagi_server.shutdown()

    def run(self):
        self._fagi_server.serve_forever()


if __name__ == '__main__':
    fastagi_core = FastAGIServer()
    fastagi_core.start()

    while fastagi_core.is_alive():
        # In a larger application, you'd probably do something useful in another non-daemon
        # thread or maybe run a parallel AMI server
        time.sleep(1)
    fastagi_core.kill()
