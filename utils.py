import inspect
import re
import threading
import time

lock = threading.Lock()
MOUSE_CLICK_ENABLE = "\x1b[?1000h\x1b[?1006h"
MOUSE_CLICK_DISABLE = "\x1b[?1000l\x1b[?1006l"
MOUSE_PATTERN = re.compile(r'\x1b\[<(\d+);(\d+);(\d+)([Mm])')
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


def parse_mouse_event(sequence):
    if match := MOUSE_PATTERN.match(sequence):
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

    def __len__(self):
        return len(self.text)

    def __str__(self):
        return self.apply(self.text)

    def __repr__(self):
        return f"UIText({repr(self.text)})"

    def __add__(self, other):
        return UIText(str(self) + other)

    def __radd__(self, other):
        return UIText(other + str(self))


class HGap:
    pos = [0, 0]

    def __init__(self, count=1):
        self.count = count


class Displayable:
    pass


class VGap:
    pos = [0, 0]

    def __init__(self, count=1):
        self.count = count


class VPos:
    pos = [0, 0]

    def __init__(self, count=1):
        self.count = count


class UnBreak:
    pos = [0, 0]


class Label(Displayable):
    pos = [0, 0]

    def __init__(self, channel, terminal, text):
        self.text = text
        self.channel = channel
        self.terminal = terminal

    def draw(self):
        draw(self.pos, self.text, self.channel, self.terminal)

    def __len__(self):
        return len(self.text)


class Input(Displayable):
    pos = [0, 0]

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

    def __len__(self):
        return len(self.prompt) + len(self.text) + 1

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

        draw(self.pos, prompt + text, self.channel, self.terminal)

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
        elif data.isprintable():
            for char in data[::-1]:
                self._text.insert(self.cursor_pos, char)
            self.cursor_pos += len(data)


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
        pos, old_pos = [0, 0], 0
        for i, element in enumerate(self.elements):
            print(element, pos, old_pos)
            if isinstance(element, Label):
                element.pos = pos
                element.draw()
            elif isinstance(element, HGap):
                pos[0] += element.count - 1
            elif isinstance(element, VGap):
                pos[1] += element.count
                continue
            elif isinstance(element, VPos):
                pos[1] = element.count
                continue
            elif isinstance(element, UnBreak):
                pos[0] -= 1
                for elm in self.elements[i-1::-1]:
                    if isinstance(elm, Displayable):
                        if elm.pos[0] == pos[0]:
                            pos[1] += old_pos + len(elm)
                        break
                continue
            elif isinstance(element, Input):
                element.pos = pos
                element.draw()

            pos[0] += 1
            old_pos = pos[1]
            pos[1] = 0

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
        elif mouse := parse_mouse_event(data):
            if mouse['event_type'] == 'press':
                for i, input_ in enumerate(self.inputs):
                    if input_.pos[0] == mouse['y'] - 1:
                        self.activate(i)
                        break
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
                    self.elements.append(HGap(int(value)))
                elif key == "padding-bottom":
                    appendings.append(HGap(int(value)))
                elif key == "padding-left":
                    self.elements.append(VGap(int(value)))
                elif key == "padding-right":
                    appendings.append(VGap(int(value)))
                elif key == "margin-left":
                    self.elements.append(VPos(int(value)))
                elif key == "margin-right":
                    appendings.append(VPos(int(value)))
                elif key == "inline":
                    if value:
                        self.elements.append(UnBreak())
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
