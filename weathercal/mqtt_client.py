import socket
import struct

from .compat import ticks_diff, ticks_ms


class MQTTError(OSError):
    pass


class MQTTClient:
    def __init__(
        self,
        client_id,
        host,
        port=1883,
        user=None,
        password=None,
        keepalive=60,
    ):
        self.client_id = _bytes(client_id)
        self.host = host
        self.port = port
        self.user = _bytes(user) if user else None
        self.password = _bytes(password) if password else None
        self.keepalive = keepalive
        self.socket = None
        self.callback = None
        self.last_io = ticks_ms()
        self.packet_id = 0

    def set_callback(self, callback):
        self.callback = callback

    def connect(self):
        address = socket.getaddrinfo(self.host, self.port)[0][-1]
        self.socket = socket.socket()
        self.socket.settimeout(5)
        self.socket.connect(address)
        flags = 0x02
        payload = _field(self.client_id)
        if self.user is not None:
            flags |= 0x80
            payload += _field(self.user)
        if self.password is not None:
            flags |= 0x40
            payload += _field(self.password)
        variable = _field(b"MQTT") + bytes((4, flags)) + struct.pack(
            "!H", self.keepalive
        )
        self._write_packet(0x10, variable + payload)
        packet_type, payload = self._read_packet()
        if packet_type != 0x20 or len(payload) != 2 or payload[1] != 0:
            raise MQTTError("MQTT connection rejected")
        self.socket.settimeout(0)

    def disconnect(self):
        if self.socket:
            try:
                self.socket.write(b"\xe0\x00")
            except OSError:
                pass
            self.socket.close()
        self.socket = None

    def subscribe(self, topic):
        self.packet_id = (self.packet_id % 65535) + 1
        payload = struct.pack("!H", self.packet_id) + _field(_bytes(topic)) + b"\x00"
        self._write_packet(0x82, payload)

    def check_msg(self):
        if not self.socket:
            raise MQTTError("MQTT is disconnected")
        try:
            packet_type, payload = self._read_packet(nonblocking=True)
        except OSError as exc:
            if _would_block(exc):
                packet_type = None
                payload = None
            else:
                raise
        if packet_type == 0x30 and payload is not None:
            length = struct.unpack("!H", payload[:2])[0]
            topic = payload[2 : 2 + length]
            message = payload[2 + length :]
            if self.callback:
                self.callback(topic, message)
        elif packet_type == 0xD0:
            pass
        if ticks_diff(ticks_ms(), self.last_io) >= self.keepalive * 500:
            self._write_packet(0xC0, b"")

    def _write_packet(self, header, payload):
        packet = bytes((header,)) + _remaining_length(len(payload)) + payload
        self.socket.write(packet)
        self.last_io = ticks_ms()

    def _read_packet(self, nonblocking=False):
        first = self.socket.read(1)
        if not first:
            if nonblocking:
                raise OSError(11)
            raise MQTTError("MQTT connection closed")
        multiplier = 1
        remaining = 0
        while True:
            encoded = self.socket.read(1)
            if not encoded:
                raise MQTTError("truncated MQTT packet")
            value = encoded[0]
            remaining += (value & 127) * multiplier
            if value & 128 == 0:
                break
            multiplier *= 128
        payload = _read_exact(self.socket, remaining)
        self.last_io = ticks_ms()
        return first[0] & 0xF0, payload


def _field(value):
    return struct.pack("!H", len(value)) + value


def _bytes(value):
    return value if isinstance(value, bytes) else str(value).encode()


def _remaining_length(value):
    result = bytearray()
    while True:
        encoded = value % 128
        value //= 128
        if value:
            encoded |= 128
        result.append(encoded)
        if not value:
            return bytes(result)


def _read_exact(sock, length):
    chunks = bytearray()
    while len(chunks) < length:
        chunk = sock.read(length - len(chunks))
        if not chunk:
            raise MQTTError("truncated MQTT packet")
        chunks.extend(chunk)
    return bytes(chunks)


def _would_block(exc):
    code = exc.args[0] if exc.args else None
    return code in (11, 35, 110, 115, 116)
