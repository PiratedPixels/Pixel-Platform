import re

from blessed import Terminal
from utils import draw, send

term = Terminal()

MOUSE_CLICK_ENABLE = "\x1b[?1000h\x1b[?1006h"
MOUSE_CLICK_DISABLE = "\x1b[?1000l\x1b[?1006l"


def parse_mouse_event(sequence):
    pattern = r'\x1b\[<(\d+);(\d+);(\d+)([Mm])'
    match = re.match(pattern, sequence)
    if match:
        button_code = int(match.group(1))
        x = int(match.group(2))
        y = int(match.group(3))
        event_type = 'press' if match.group(4) == 'M' else 'release'
        return {
            'button_code': button_code,
            'x': x,
            'y': y,
            'event_type': event_type
        }
    return None


def handle_client(chan):
    options = ["Option 1", "Option 2", "Option 3"]
    descriptions = ["Description 1", "Description 2", "Description 3"]
    selected_option_index = 0

    send(term.clear)
    draw((0, 0), term.bold(term.red('Hey what do you want to do?!')))
    send(term.hide_cursor)
    send(MOUSE_CLICK_ENABLE)

    try:
        while True:
            for i, option in enumerate(options):
                if i == selected_option_index:
                    option = term.green("● ") + option + term.lightcyan4(f" ({descriptions[i]})")
                else:
                    option = term.lightcyan4("○ " + option)

                draw((2 + i, 0), option)

            draw((4 + i, 0), term.cyan(f'Press q to quit.'))

            raw_data = chan.recv(1024)
            data = raw_data.decode('utf-8').strip()
            print(f"Received: {repr(data)}")
            if data == 'q':
                break
            elif data == '\x1b[B':
                selected_option_index = (selected_option_index + 1) % len(options)
            elif data == '\x1b[A':
                selected_option_index = (selected_option_index - 1) % len(options)
            elif data == '':
                pass
            elif mouse := parse_mouse_event(data):
                if mouse['event_type'] == 'press':
                    line = mouse['y'] - 3
                    if 0 <= line < len(options):
                        selected_option_index = line
    finally:
        send(term.normal_cursor)
        send(term.clear)
        send(MOUSE_CLICK_DISABLE)
        chan.close()
