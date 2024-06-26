import re
from threading import Thread

from blessed import Terminal
from utils import Layout

term = Terminal()
term.rgb = term.color_rgb


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

def receive_input(chan, layout):
    while layout.running:
        data = chan.recv(1024).decode('utf-8')
        if data.strip().lower() == "q" and layout.active_input_index is None:
            layout.running = False
            break

        layout.handle_input(data)


def postcheck(layout):
    if layout.active_input_index is not None:
        layout.named_elements["enter"].text = "Press Enter to Continue"
        layout.named_elements["exit"].text = "Press Esc to Stop Typing"
    else:
        layout.named_elements["enter"].text = "Press Enter to Login"
        layout.named_elements["exit"].text = "Press Q to Exit"


def click_handler(layout, elm):
    if not hasattr(elm, "id"):
        return
    if elm.id == "exit":
        if layout.active_input_index is None:
            layout.handle_input("q")
        else:
            layout.handle_input("\x1b")
    elif elm.id == "enter":
        if layout.active_input_index is not None:
            layout.handle_input("")
        else:
            print("Logged in with {} and {}".format(layout.named_elements["username"].raw, layout.named_elements["password"].raw))


def handle_client(chan):
    layout = Layout(chan, term, postcheck, click_handler)
    layout.load_layout("ui.layout")

    layout.running = True
    Thread(target=receive_input, args=(chan, layout)).start()

    with layout:
        while layout.running:
            layout.draw()
