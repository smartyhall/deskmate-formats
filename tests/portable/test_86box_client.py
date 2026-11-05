"""ROM-free protocol transport, evidence and mutation-failure controls."""
import base64
import importlib.util
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch
import zlib

SPEC = importlib.util.spec_from_file_location(
    'box_client', Path(__file__).resolve().parents[2] / 'tools/86box_client.py')
box = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(box)


def line(**fields):
    return json.dumps(dict(ok=True, **fields)).encode() + b'\n'


class Wire:
    def __init__(self, replies):
        self.chunks = list(replies)
        self.sent = []
        self.closed = False

    def settimeout(self, timeout):
        self.timeout = timeout

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, count):
        if not self.chunks:
            return b''
        chunk = self.chunks.pop(0)
        result, rest = chunk[:count], chunk[count:]
        if rest:
            self.chunks.insert(0, rest)
        return result

    def close(self):
        self.closed = True


def png_chunk(kind, data):
    raw = kind + data
    return struct.pack('>I', len(data)) + raw + struct.pack('>I', zlib.crc32(raw))


def synthetic_png():
    return (b'\x89PNG\r\n\x1a\n'
            + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + png_chunk(b'IDAT', zlib.compress(b'\0\x11\x22\x33'))
            + png_chunk(b'IEND', b''))


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.token = 'a1' * 32
        self.token_file = self.root / 'automation.token'
        self.token_file.write_text(self.token)
        self.journal = self.root / 'private.jsonl'

    def tearDown(self):
        self.temp.cleanup()

    def client(self, replies, **kwargs):
        wire = Wire([line(auth=True)] + replies)
        with patch.object(box.socket, 'create_connection', return_value=wire):
            client = box.Client(self.token_file, journal=self.journal, **kwargs)
        self.addCleanup(client.close)
        return client, wire

    def test_fragmented_and_coalesced_json_preserves_framing(self):
        reply = line(protocol=1, held=True)
        client, wire = self.client([reply[:3], reply[3:] + line(machine='SYNTHETIC')])
        self.assertEqual(client.status()['protocol'], 1)
        self.assertEqual(client.info()['machine'], 'SYNTHETIC')
        self.assertEqual(len(wire.sent), 3)
        self.assertNotIn(self.token, self.journal.read_text())

    def test_real_loopback_authentication_and_fragmentation(self):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(3)
        errors = []

        def serve():
            try:
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(3)
                    stream = conn.makefile('rb')
                    self.assertEqual(stream.readline(), ('auth ' + self.token + '\n').encode())
                    conn.sendall(line(auth=True))
                    self.assertEqual(stream.readline(), b'status\n')
                    reply = line(protocol=1, version='SYNTHETIC')
                    for chunk in (reply[:1], reply[1:9], reply[9:]):
                        conn.sendall(chunk)
                    stream.close()
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        try:
            with box.Client(self.token_file, port=listener.getsockname()[1], timeout=3) as client:
                self.assertEqual(client.status()['version'], 'SYNTHETIC')
        finally:
            listener.close()
            worker.join(4)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])

    def test_authentication_rejection_closes_transport_without_logging_token(self):
        wire = Wire([b'{"ok":false,"error":"authentication required"}\n'])
        with patch.object(box.socket, 'create_connection', return_value=wire):
            with self.assertRaises(box.ProtocolError):
                box.Client(self.token_file, journal=self.journal)
        self.assertTrue(wire.closed)
        self.assertFalse(self.journal.exists())

    def test_invalid_token_and_remote_endpoint_rejected_before_connect(self):
        with patch.object(box.socket, 'create_connection') as connect:
            with self.assertRaises(ValueError):
                box.Client(self.token_file, host='192.0.2.1')
            self.token_file.write_text('invalid')
            with self.assertRaises(ValueError):
                box.Client(self.token_file)
            connect.assert_not_called()

    def test_bad_oversized_fatal_and_eof_replies_invalidate_connection(self):
        for response in (b'{bad}\n', b'[]\n', b'x' * 200,
                         b'{"ok":false,"fatal":true}\n', b'{"ok":true'):
            with self.subTest(response=response[:20]):
                client, wire = self.client([response], max_reply=128)
                with self.assertRaises(box.ProtocolError):
                    client.info()
                self.assertTrue(wire.closed)

    def test_lost_key_reply_is_never_replayed(self):
        client, wire = self.client([b''])
        with self.assertRaises(box.ProtocolError):
            client.tap(28)
        self.assertEqual(wire.sent[1:], [b'key down 0x1c\n'])
        self.assertIn('uncertain', self.journal.read_text())
        with self.assertRaises(box.ProtocolError):
            client.tap(28)

    def test_partial_reply_cannot_extend_total_deadline(self):
        client, wire = self.client([b'{', b'"', b'o', b'k'])
        with patch.object(box.time, 'monotonic', side_effect=[0, 1, 16]):
            with self.assertRaises(box.ProtocolError):
                client.info()
        self.assertTrue(wire.closed)
        self.assertEqual(wire.sent[1:], [b'info\n'])

    def test_command_rejection_keeps_framing(self):
        client, _ = self.client([b'{"ok":false,"error":"graphics mode"}\n', line(protocol=1)])
        with self.assertRaisesRegex(box.CommandError, 'graphics mode'):
            client.text()
        self.assertEqual(client.status()['protocol'], 1)

    def test_cp437_and_memory_integrity(self):
        client, _ = self.client([line(chars=['da41'], attrs=['0707'], cols=2, rows=1),
                                 line(addr=0x400, data='1234')])
        self.assertEqual(client.text()['lines'], ['┌A'])
        self.assertEqual(client.memory(0x400, 2), b'\x12\x34')
        for reply in (line(addr=0x400, data='12'), line(addr=0x401, data='1234')):
            client, _ = self.client([reply])
            with self.assertRaises(box.ProtocolError):
                client.memory(0x400, 2)

    def test_protocol_and_input_validation_precedes_wire_mutation(self):
        client, wire = self.client([])
        invalid = [lambda: client._call('status\nquit'), lambda: client.memory(-1, 2),
                   lambda: client.memory(0, 65537), lambda: client.key('down', 0x200),
                   lambda: client.type_ascii('valid prefix\u2603'), lambda: client.floppy(2),
                   lambda: client.reset('unknown')]
        for operation in invalid:
            with self.assertRaises(ValueError):
                operation()
        self.assertEqual(len(wire.sent), 1)

    def test_png_dimensions_crc_and_truncation(self):
        png = synthetic_png()
        for payload, width, success in ((png, 1, True), (png, 2, False),
                                        (png[:-1], 1, False), (png[:-4] + b'xxxx', 1, False)):
            client, _ = self.client([line(png=base64.b64encode(payload).decode(), w=width, h=1)])
            if success:
                self.assertEqual(client.framebuffer()[0], png)
            else:
                with self.assertRaises(box.ProtocolError):
                    client.framebuffer()

    def test_step_checks_actual_time_and_quantum(self):
        status = dict(protocol=1, held=True, paused=False, quantum_ms=10, ms=100)
        client, wire = self.client([line(**status)])
        with self.assertRaises(ValueError):
            client.step(11)
        self.assertEqual(wire.sent[-1], b'status\n')
        client, _ = self.client([line(**status), line(ms=110), line(**dict(status, ms=110))])
        self.assertEqual(client.step(10)['actual_delta_ms'], 10)
        client, _ = self.client([line(**status), line(ms=105), line(**dict(status, ms=105))])
        with self.assertRaisesRegex(box.ProtocolError, 'actual 5'):
            client.step(10)

    def test_observation_rejects_reset_or_time_changes(self):
        status = dict(protocol=1, held=True, paused=False, ms=100, frames=2,
                      bios_mode=19, w=1, h=1, version='SYNTHETIC')
        info = dict(machine='SYNTHETIC', version='SYNTHETIC', hard_resets=1,
                    soft_resets=0, last_reset_ms=0)
        for change in ('none', 'time', 'reset'):
            client, _ = self.client([line(), line(**status), line(**info), line(eax=123),
                line(**dict(status, ms=101 if change == 'time' else 100)),
                line(**dict(info, hard_resets=2 if change == 'reset' else 1))])
            if change == 'none':
                self.assertEqual(client.observe()[0]['registers']['eax'], 123)
            else:
                with self.assertRaisesRegex(box.ProtocolError, 'inconsistent'):
                    client.observe()


if __name__ == '__main__':
    unittest.main()
