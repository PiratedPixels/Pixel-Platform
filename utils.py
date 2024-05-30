import inspect
import threading

lock = threading.Lock()


def draw(pos, text):
    bf = inspect.currentframe().f_back
    chan = bf.f_locals["chan"]
    terminal = bf.f_globals["term"]

    lock.acquire()
    send(terminal.move_yx(*pos))
    send(terminal.clear_eol())
    send(text)
    lock.release()


def send(text):
    bf = inspect.currentframe().f_back
    chan = bf.f_locals["chan"]
    chan.send(text.encode())
