import inspect


def draw(pos, text):
    bf = inspect.currentframe().f_back
    chan = bf.f_locals["chan"]
    terminal = bf.f_globals["term"]

    send(terminal.move_yx(*pos))
    send(terminal.clear_eol())
    send(text)


def send(text):
    bf = inspect.currentframe().f_back
    chan = bf.f_locals["chan"]
    chan.send(text.encode())