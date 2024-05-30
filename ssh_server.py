import importlib
import signal
import dotenv
import paramiko
import socket
import threading
import ssh_tui
import os

from blessed import Terminal

dotenv.load_dotenv()

HOST_KEY = paramiko.RSAKey(filename=os.environ["SSH_KEY_PATH"])
USERNAME = os.environ["SSH_USERNAME"]
PASSWORD = os.environ["SSH_PASSWORD"]
SSH_PORT = int(os.environ["SSH_PORT"])

term = Terminal()
running = True


class SSHServer(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if username == USERNAME and password == PASSWORD:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True


def signal_handler(*_):
    global running
    running = False
    print(term.red("\nServer is shutting down..."))


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', SSH_PORT))
    server_socket.listen(100)
    print(term.green(f"Listening for connection on port {SSH_PORT}..."))

    signal.signal(signal.SIGINT, signal_handler)

    while running:
        try:
            server_socket.settimeout(.1)
            client_socket, addr = server_socket.accept()
        except socket.timeout:
            continue
        print(term.cyan(f"Connection from {addr}"))

        transport = paramiko.Transport(client_socket)
        transport.add_server_key(HOST_KEY)
        server = SSHServer()

        try:
            transport.start_server(server=server)
        except paramiko.SSHException:
            print(term.red("SSH negotiation failed."))
            continue

        chan = transport.accept(20)
        if chan is None:
            print(term.red("No channel."))
            continue

        print(term.green("Authenticated!"))
        if not server.event.wait(10):
            print(term.yellow("Client never asked for a shell."))
            continue

        lib = importlib.reload(ssh_tui)

        threading.Thread(target=lib.handle_client, args=(chan,), daemon=True).start()

    server_socket.close()


if __name__ == "__main__":
    start_server()
