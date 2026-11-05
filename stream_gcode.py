"""Send a G-code file to a GRBL controller, one line at a time.

Written in 2026 for this repo. Not the original streaming setup.

    python3 stream_gcode.py /dev/ttyACM0 shape.nc
"""
import re
import sys
import time

import serial  # pip install pyserial


def send(port, line):
    """Send one line and wait until GRBL answers ok."""
    port.write((line + '\n').encode())
    while True:
        reply = port.readline().decode(errors='ignore').strip()
        if reply == 'ok':
            return
        if reply.startswith('error') or reply.startswith('ALARM'):
            raise RuntimeError(f'{line} -> {reply}')
        if reply:
            print('  grbl:', reply)  # start-up text or [MSG:...]


def main():
    if len(sys.argv) != 3:
        sys.exit('usage: stream_gcode.py PORT FILE')

    port = serial.Serial(sys.argv[1], 115200, timeout=5)
    time.sleep(2)  # GRBL resets when the port opens
    port.reset_input_buffer()

    send(port, '$H')  # home first
    with open(sys.argv[2]) as f:
        for n, raw in enumerate(f, 1):
            line = re.sub(r'\([^)]*\)', '', raw).split(';')[0].strip()  # drop comments
            if line:
                send(port, line)
                print(f'{n:5d}  {line}')
    print('done')


if __name__ == '__main__':
    main()
