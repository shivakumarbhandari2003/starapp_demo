"""Minimal RFC 6455 websocket client (text frames) - enough for the Chrome DevTools protocol."""
import base64
import os
import socket
import struct

CRLF = b"\r\n"


class WS:
    def __init__(self, url):
        assert url.startswith("ws://")
        hostport, path = url[5:].split("/", 1)
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = ("GET /" + path + " HTTP/1.1\r\nHost: " + hostport + "\r\nUpgrade: websocket\r\n"
               "Connection: Upgrade\r\nSec-WebSocket-Key: " + key + "\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        buf = b""
        while CRLF + CRLF not in buf:
            buf += self.sock.recv(4096)
        self.rest = buf.split(CRLF + CRLF, 1)[1]

    def _read(self, n):
        out = b""
        while len(out) < n:
            if self.rest:
                take = self.rest[:n - len(out)]
                self.rest = self.rest[len(take):]
                out += take
                continue
            chunk = self.sock.recv(max(65536, n - len(out)))
            if not chunk:
                raise EOFError("socket closed")
            self.rest = chunk
        return out

    def send(self, text):
        data = text.encode()
        mask = os.urandom(4)
        n = len(data)
        hdr = bytes([0x81])
        if n < 126:
            hdr += bytes([0x80 | n])
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.sock.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        message = b""
        while True:
            b1, b2 = self._read(2)
            op, fin = b1 & 0x0F, b1 & 0x80
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            if op in (0, 1):
                message += payload
                if fin:
                    return message.decode()

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def connect(url, max_size=None):
    return WS(url)
