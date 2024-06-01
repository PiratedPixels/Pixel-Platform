import inspect
import threading
import time

lock = threading.Lock()
MOUSE_CLICK_ENABLE = "\x1b[?1000h\x1b[?1006h"
MOUSE_CLICK_DISABLE = "\x1b[?1000l\x1b[?1006l"
FPS = 20


def draw(pos, text, channel, terminal):
    with lock:
        send(terminal.move_yx(*pos), channel)
        send(terminal.clear_eol(), channel)
        send(text, channel)


def send(text, channel):
    channel.send(text)


class Gap:
    pos = 0

    def __init__(self, count=1):
        self.count = count


class Label:
    pos = 0

    def __init__(self, text, color, channel, terminal):
        self.text = text
        self.color = color
        self.channel = channel
        self.terminal = terminal

    def draw(self):
        fg_text = self.text
        if self.color and fg_text:
            fg_text = self.color(self.text)
        draw((self.pos, 0), fg_text, self.channel, self.terminal)


class TextInput:
    pos = 0

    def __init__(self, prompt, placeholder, hidden, prompt_format, placeholder_format, channel, terminal):
        self.prompt = prompt
        self.placeholder = placeholder
        self.hidden = hidden
        self.prompt_format = prompt_format
        self.placeholder_format = placeholder_format
        self.channel = channel
        self.terminal = terminal

        self.active = False
        self._cursor = 0
        self._cursor_pos = None
        self._text = []

    @property
    def cursor(self):
        self._cursor += 1
        self._cursor %= FPS
        if self.active:
            return '|' * (self._cursor < FPS / 2)
        return ''

    @property
    def cursor_pos(self):
        return len(self._text) if self._cursor_pos is None else self._cursor_pos

    @cursor_pos.setter
    def cursor_pos(self, value):
        self._cursor_pos = min(max(0, value), len(self._text)) if isinstance(value, int) else None

    @property
    def text(self):
        if not self._text:
            return self.placeholder
        return '*' * len(self._text) if self.hidden else "".join(self._text)

    def apply_format(self, text):
        format_ = self.placeholder_format
        return format_(text[:self.cursor_pos]) + self.cursor + format_(text[self.cursor_pos:]) if self.active else format_(text)

    def draw(self):
        prompt = self.placeholder
        if self.prompt_format and prompt:
            prompt = self.prompt_format(self.prompt)

        text = self.text
        if self.placeholder_format and text:
            text = self.apply_format(text)

        draw((self.pos, 0), prompt + text, self.channel, self.terminal)

    def handle_input(self, data):
        if data == '\x1b[C':
            self.cursor_pos += 1
        elif data == '\x1b[D':
            self.cursor_pos -= 1
        elif data == '\x7f':
            if self.cursor_pos:
                self._text.pop(self.cursor_pos - 1)
                self.cursor_pos -= 1
        elif data == '\x1b[3~':
            if 0 <= self.cursor_pos + 1 <= len(self._text):
                self._text.pop(self.cursor_pos)
        elif len(data) == 1:
            self._text.insert(self.cursor_pos, data)
            self.cursor_pos += 1


class Layout:
    def __init__(self, channel, terminal):
        self.channel = channel
        self.terminal = terminal
        self.elements = []

        self.inputs = []
        self.active_input_index = None

    def add_label(self, text, color=None):
        label = Label(text, color, self.channel, self.terminal)
        self.elements.append(label)
        return label

    def add_gap(self, size):
        gap = Gap(size)
        self.elements.append(gap)
        return gap

    def add_input(self, prompt, placeholder, hidden=False, prompt_format=None, placeholder_format=None):
        if placeholder_format is None:
            placeholder_format = self.terminal.lightcyan4
        elm = TextInput(prompt, placeholder, hidden, prompt_format, placeholder_format, self.channel, self.terminal)
        self.elements.append(elm)
        self.inputs.append(elm)
        if len(self.inputs) == 1:
            self.activate(0)
        return elm

    def activate(self, index):
        if self.active_input_index is not None:
            self.inputs[self.active_input_index].active = False
            self.inputs[self.active_input_index].draw()

        if 0 <= index < len(self.inputs):
            self.active_input_index = index
            self.inputs[self.active_input_index].active = True
        else:
            self.active_input_index = None

    def init(self):
        i = 0
        for element in self.elements:
            if isinstance(element, Label):
                element.pos = i
                element.draw()
            elif isinstance(element, Gap):
                i += element.count - 1
            elif isinstance(element, TextInput):
                element.pos = i
                element.draw()
            i += 1

    def draw(self):
        for element in self.inputs:
            if element.active:
                element.draw()
        time.sleep(1 / FPS)

    def handle_input(self, data):
        # print(f"Received: {repr(data)}")
        if data == '\x1b[B' or data == '' or data == '\r':
            if self.active_input_index is not None:
                self.activate(self.active_input_index + 1)
            else:
                self.activate(0)
        elif data == '\x1b[A':
            if self.active_input_index is not None:
                self.activate(self.active_input_index - 1)
            else:
                self.activate(len(self.inputs) - 1)
        elif data == '\x1b':
            self.activate(-1)
        elif self.active_input_index is not None:
            self.inputs[self.active_input_index].handle_input(data)

    def __enter__(self):
        send(self.terminal.clear, self.channel)
        send(self.terminal.hide_cursor, self.channel)
        send(MOUSE_CLICK_ENABLE, self.channel)
        self.init()

    def __exit__(self, exc_type, exc_val, exc_tb):
        send(self.terminal.normal_cursor, self.channel)
        send(self.terminal.clear, self.channel)
        send(MOUSE_CLICK_DISABLE, self.channel)
        self.channel.close()

