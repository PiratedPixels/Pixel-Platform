from blessed import Terminal
from utils import draw, send

term = Terminal()


def handle_client(chan):
    options = ["Option 1", "Option 2", "Option 3"]
    descriptions = ["Description 1", "Description 2", "Description 3"]
    selected_option_index = 0

    with term.fullscreen(), term.cbreak():
        send(term.clear)
        draw((0, 0), term.bold(term.red('Hey what do you want to do?!')))
        send(term.hide_cursor)

        try:
            while True:
                for i, option in enumerate(options):
                    if i == selected_option_index:
                        option = term.green("● ") + option + term.lightcyan4(f" ({descriptions[i]})")
                    else:
                        option = term.lightcyan4("○ " + option)

                    draw((2 + i, 0), option)

                draw((4 + i, 0), term.cyan(f'Press q to quit.'))

                data = chan.recv(1024).decode('utf-8').strip()
                print(f"Received: {repr(data)}")
                if data == 'q':
                    break
                elif data == '\x1b[B':
                    selected_option_index = (selected_option_index + 1) % len(options)
                elif data == '\x1b[A':
                    selected_option_index = (selected_option_index - 1) % len(options)
                elif data == '':
                    pass
        finally:
            send(term.normal_cursor)
            send(term.clear)
            chan.close()
