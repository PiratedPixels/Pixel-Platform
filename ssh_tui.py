import re
import time
from threading import Thread

from blessed import Terminal
from utils import draw, send, Layout

term = Terminal()


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


# def handle_client2(chan):
#     options = ["Username - ", "Password - "]
#     values = ["", ""]
#     selected_option_index = 0
#     running = True
#
#     send(term.clear)
#     draw((0, 0), term.bold(term.red('Welcome to the Pixel Platform! Please login to continue.')))
#     send(term.hide_cursor)
#     send(MOUSE_CLICK_ENABLE)
#
#     def do_blink():
#         nonlocal chan
#         blink = True
#         while running:
#             i = selected_option_index
#             option = term.green("● ") + options[i] + term.lightcyan4(values[i] + ('|' if blink else ''))
#             draw((2 + i, 0), option)
#             blink = not blink
#             time.sleep(.5)
#
#     Thread(target=do_blink).start()
#
#     try:
#         while running:
#             for i, option in enumerate(options):
#                 if i == selected_option_index:
#                     option = term.green("● ") + option + term.lightcyan4(values[i]) + term.lightcyan4("|")
#                 else:
#                     option = term.lightcyan4("○ " + option + term.lightcyan4(values[i]))
#
#                 draw((2 + i, 0), option)
#
#             draw((4 + i, 0), term.cyan(f'Press q to quit.'))
#
#             raw_data = chan.recv(1024)
#             data = raw_data.decode('utf-8').strip()
#             print(f"Received: {repr(data)}")
#             if data.lower() == 'q':
#                 break
#             elif data == '\x1b[B':
#                 selected_option_index = (selected_option_index + 1) % len(options)
#             elif data == '\x1b[A':
#                 selected_option_index = (selected_option_index - 1) % len(options)
#             elif data == '':
#                 if selected_option_index == 0:
#                     selected_option_index = 1
#             elif mouse := parse_mouse_event(data):
#                 if mouse['event_type'] == 'press':
#                     line = mouse['y'] - 3
#                     if 0 <= line < len(options):
#                         selected_option_index = line
#             elif data.isprintable():
#                 values[selected_option_index] += data
#             elif data == '\x7f':
#                 values[selected_option_index] = values[selected_option_index][:-1]
#     finally:
#         running = False
#         send(term.normal_cursor)
#         send(term.clear)
#         send(MOUSE_CLICK_DISABLE)
#         chan.close()

def handle_client(chan):
    layout = Layout(chan, term)

    layout.add_label('Welcome to the Pixel Platform! Please login to continue.', term.red)
    layout.add_gap(1)
    layout.add_label("Username - ", term.color_rgb(122, 127, 255))
    layout.add_label("Password - ", term.blue)
    layout.add_gap(1)
    layout.add_label('Press Q to Quit', term.pink)

    with layout:
        while True:
            layout.draw()
            if chan.recv(1024).decode('utf-8').strip().lower() == "q":
                break
