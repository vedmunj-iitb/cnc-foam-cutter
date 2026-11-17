"""A small fake GRBL on a Linux pseudo-terminal, to try stream_gcode.py without the machine.

Written in 2026 for this repo. It is not GRBL and it moves nothing. It answers "ok" to every
line it receives, after a short delay, and prints what it got and what it answered.

    python3 tools/fake_grbl.py ttyFAKE &
    sleep 1
    python3 stream_gcode.py ttyFAKE examples/square.nc

--reply 'TEXT=REPLY' answers REPLY instead of ok to the line TEXT, for example
--reply '$H=error:5' to see the streamer stop. If nothing connects within --wait seconds, it quits.
"""
import argparse
import os
import select
import signal
import sys
import time
import tty

COLOUR = sys.stdout.isatty()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('link', help='name of the link to the pseudo-terminal, for example ttyFAKE')
    ap.add_argument('--delay', type=float, default=0.3, help='seconds before each answer')
    ap.add_argument('--reply', action='append', default=[], metavar='TEXT=REPLY')
    ap.add_argument('--idle-exit', type=float, default=0.5,
                    help='quit after this many quiet seconds, once a line has arrived')
    ap.add_argument('--wait', type=float, default=30.0,
                    help='quit if no line arrives within this many seconds')
    args = ap.parse_args()
    if any('=' not in r for r in args.reply):
        ap.error('use --reply TEXT=REPLY')
    special = dict(r.rsplit('=', 1) for r in args.reply)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # so the link below is removed on kill

    master, slave = os.openpty()
    tty.setraw(slave)  # no echo, no line editing, like a serial port
    if os.path.lexists(args.link):
        os.remove(args.link)
    os.symlink(os.ttyname(slave), args.link)
    extra = ''.join(f', {r} to "{t}"' for t, r in special.items())
    print(f'fake GRBL on {args.link}, answers ok to each line{extra}', flush=True)

    buf = b''
    got_any = False
    try:
        while True:
            ready, _, _ = select.select([master], [], [], args.idle_exit if got_any else args.wait)
            if not ready:
                if not got_any:
                    print('fake GRBL: no connection, quitting', flush=True)
                break
            buf += os.read(master, 1024)
            while b'\n' in buf:
                raw, buf = buf.split(b'\n', 1)
                line = raw.decode(errors='replace').strip()
                if not line:
                    continue
                got_any = True
                reply = special.get(line, 'ok')
                time.sleep(args.delay)
                shown = reply
                if COLOUR:  # grey for the fake's own lines, green ok, red for anything else
                    shown = f'\033[{"32" if reply == "ok" else "31"}m{reply}\033[90m'
                    print(f'\033[90m    fake grbl  got {line:<16} answers {shown}\033[0m', flush=True)
                else:
                    print(f'    fake grbl  got {line:<16} answers {shown}', flush=True)
                os.write(master, (reply + '\r\n').encode())
    finally:
        os.remove(args.link)


if __name__ == '__main__':
    main()
