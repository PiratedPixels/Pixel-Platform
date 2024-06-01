import inspect
import threading

lock = threading.Lock()
MOUSE_CLICK_ENABLE = "\x1b[?1000h\x1b[?1006h"
MOUSE_CLICK_DISABLE = "\x1b[?1000l\x1b[?1006l"


def draw(pos, text, channel, terminal):
    with lock:
        send(terminal.move_yx(*pos), channel)
        send(terminal.clear_eol(), channel)
        send(text, channel)


def send(text, channel):
    channel.send(text)


class Gap:
    def __init__(self, count=1):
        self.count = count


class Label:
    def __init__(self, text, color, channel, terminal):
        self.text = text
        self.color = color
        self.channel = channel
        self.terminal = terminal

    def draw(self, pos):
        fg_text = self.text
        if self.color:
            fg_text = self.color(self.text)
        draw(pos, fg_text, self.channel, self.terminal)


class Layout:
    initialized = False

    def __init__(self, channel, terminal):
        self.channel = channel
        self.terminal = terminal
        self.elements = []

    def add_label(self, text, color=None):
        label = Label(text, color, self.channel, self.terminal)
        self.elements.append(label)
        return label

    def add_gap(self, size):
        gap = Gap(size)
        self.elements.append(gap)
        return gap

    def draw(self):
        i = 0
        for element in self.elements:
            if isinstance(element, Label) and not self.initialized:
                element.draw((i, 0))
            elif isinstance(element, Gap):
                i += element.count - 1
            i += 1
        self.initialized = True

    def __enter__(self):
        send(self.terminal.clear, self.channel)
        send(self.terminal.hide_cursor, self.channel)
        send(MOUSE_CLICK_ENABLE, self.channel)

    def __exit__(self, exc_type, exc_val, exc_tb):
        send(self.terminal.normal_cursor, self.channel)
        send(self.terminal.clear, self.channel)
        send(MOUSE_CLICK_DISABLE, self.channel)
        self.channel.close()

