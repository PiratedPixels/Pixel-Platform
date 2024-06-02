import inspect
import re
import threading
import time

lock = threading.Lock()
MOUSE_CLICK_ENABLE = "\x1b[?1000h\x1b[?1006h"
MOUSE_CLICK_DISABLE = "\x1b[?1000l\x1b[?1006l"
FIELD_PARSER = re.compile('^(.*? {\n.*?})$', re.DOTALL | re.MULTILINE)
PROPS_PARSER = re.compile(r'\s*.*?\n')
FPS = 20


def draw(pos, text, channel, terminal):
    with lock:
        send(terminal.move_yx(*pos), channel)
        send(terminal.clear_eol(), channel)
        send(text, channel)


def send(text, channel):
    channel.send(str(text))


class UIText:
    def __init__(self, text):
        self.text = text
        self.colors = []

    def __xor__(self, other):
        self.colors.append(other)
        return self

    def __rxor__(self, other):
        self.colors.insert(0, other)
        return self

    def apply(self, text):
        for color in self.colors:
            text = color(text)
        return text

    def __str__(self):
        return self.apply(self.text)

    def __repr__(self):
        return f"UIText({repr(self.text)})"

    def __add__(self, other):
        return UIText(str(self) + other)

    def __radd__(self, other):
        return UIText(other + str(self))


class Gap:
    pos = 0

    def __init__(self, count=1):
        self.count = count


class Label:
    pos = 0

    def __init__(self, channel, terminal, text):
        self.text = text
        self.channel = channel
        self.terminal = terminal

    def draw(self):
        draw((self.pos, 0), self.text, self.channel, self.terminal)


class Input:
    pos = 0

    def __init__(self, channel, terminal, prompt, placeholder=UIText(""), hidden=False):
        self.prompt = prompt
        self.placeholder = placeholder
        self.hidden = hidden
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
        return UIText('*' * len(self._text) if self.hidden else "".join(self._text))

    def apply_format(self, text):
        apply = self.text.apply
        text = text.text
        return apply(text[:self.cursor_pos]) + self.cursor + apply(text[self.cursor_pos:]) if self.active else apply(text)

    def draw(self):
        prompt = self.prompt
        text = self.apply_format(self.text)

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
            elif isinstance(element, Input):
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

    def load_layout(self, layout_file):
        with open(layout_file, 'r') as f:
            layout = f.read()

        fields = FIELD_PARSER.findall(layout)
        for field in fields:
            props = *map(str.strip, PROPS_PARSER.findall(field.strip())),
            field = props[0].split()[0]
            if field not in globals():
                raise ValueError(f"Field {field} not found")
            field = globals()[field]
            kwargs = {}
            appendings = []

            for prop in props[1:]:
                key, *value = prop.split(':')
                value = ':'.join(value).strip()
                key = key.strip()
                if key == "padding-top":
                    self.elements.append(Gap(int(value)))
                elif key == "padding-bottom":
                    appendings.append(Gap(int(value)))
                elif key not in inspect.signature(field.__init__).parameters:
                    raise ValueError(f"Property {key} not found in {field}")
                else:
                    values = value.split("|")
                    value = eval(values[0])
                    if isinstance(value, str):
                        value = UIText(value)
                        for color in values[1:]:
                            color = eval(f"self.terminal.{color.strip()}", globals(), locals())
                            value ^= color
                    kwargs[key] = value

            elm = field(self.channel, self.terminal, **kwargs)
            self.elements.append(elm)
            self.elements.extend(appendings)

            if isinstance(elm, Input):
                if not elm.placeholder.colors:
                    elm.placeholder.colors.append(self.terminal.lightcyan4)
                self.inputs.append(elm)
                if len(self.inputs) == 1:
                    self.activate(0)

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

