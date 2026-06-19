import unittest
from unittest import mock

from weathercal import mqtt_client
from weathercal.mqtt_client import MQTTClient


class RecordingSocket:
    def __init__(self):
        self.writes = []
        self.reads = bytearray(b"\x20\x02\x00\x00")

    def write(self, value):
        self.writes.append(value)

    def settimeout(self, value):
        pass

    def connect(self, address):
        pass

    def read(self, length):
        result = bytes(self.reads[:length])
        del self.reads[:length]
        return result


class MQTTClientTests(unittest.TestCase):
    def test_publish_supports_retained_and_non_retained_messages(self):
        client = MQTTClient("client", "broker")
        client.socket = RecordingSocket()

        client.publish("base/diagnostics", "hello")
        client.publish("base/status", '{"state":"online"}', retain=True)

        self.assertEqual(client.socket.writes[0][0], 0x30)
        self.assertEqual(client.socket.writes[1][0], 0x31)
        self.assertIn(b"base/diagnostics", client.socket.writes[0])
        self.assertIn(b"base/status", client.socket.writes[1])

    def test_connect_encodes_retained_last_will(self):
        sock = RecordingSocket()
        with mock.patch.object(
            mqtt_client.socket,
            "getaddrinfo",
            return_value=[(None, None, None, None, ("broker", 1883))],
        ), mock.patch.object(mqtt_client.socket, "socket", return_value=sock):
            client = MQTTClient(
                "screen",
                "broker",
                will_topic="base/clients/screen/status",
                will_payload='{"state":"offline"}',
                will_retain=True,
            )
            client.connect()

        packet = sock.writes[0]
        self.assertEqual(packet[0], 0x10)
        self.assertEqual(packet[9], 0x26)
        self.assertIn(b"base/clients/screen/status", packet)
        self.assertIn(b'{"state":"offline"}', packet)
