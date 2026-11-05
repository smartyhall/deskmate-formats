"""Authenticated synthetic native TCP peer; no emulator, ROM or DOS data."""
import base64
import hashlib
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import zlib


def png():
    def chunk(kind, data):
        block = kind+data
        return struct.pack('>I',len(data))+block+struct.pack('>I',zlib.crc32(block))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))
            +chunk(b'IDAT',zlib.compress(b'\0\x11\x22\x33'))+chunk(b'IEND',b''))


class NativePeer:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)/'DO_NOT_DISCLOSE'
        self.root.mkdir()
        self.token = 'ab'*32
        (self.root/'automation.token').write_text(self.token)
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1',0))
        self.listener.listen()
        self.listener.settimeout(0.1)
        self.port = self.listener.getsockname()[1]
        self.stop = threading.Event()
        self.commands = []
        self.authentications = 0
        self.failure = None
        self.held = True
        self.ms = 1000
        self.frames = 1
        self.resets = 1
        self.text_chars = 'da'
        self.bad_png = False
        self.machine = 'SYNTHETIC'
        self.version = '7.0 Beta [1234]'
        self.after_command = None
        self.disconnected = threading.Event()
        self.thread = threading.Thread(target=self.serve,daemon=True)
        self.thread.start()

    def config(self):
        return {'instances':{'fixture':{'machine_directory':str(self.root),'port':self.port,
            'expected_machine':'SYNTHETIC','expected_version':self.version,
            'ram_regions':{'canary':{'start':0x500,'length':64}},
            'ram_checkpoint':{'token_sha256':hashlib.sha256(bytes.fromhex(self.token)).hexdigest(),
                'ms':self.ms,'frames':self.frames,'hard_resets':self.resets,'soft_resets':0,
                'last_reset_ms':self.resets*100}}}}

    def respond(self, command):
        status = dict(ms=self.ms,frames=self.frames,held=self.held,paused=False,w=1,h=1,
                      bios_mode=3,protocol=1,version=self.version,quantum_ms=1)
        if command == 'status':
            return dict(ok=True,**status)
        if command == 'info':
            return dict(ok=True,version=self.version,machine=self.machine,hard_resets=self.resets,
                        soft_resets=0,last_reset_ms=self.resets*100,
                        hdd=[{'file':str(self.root/'private.img')}])
        if command == 'regs':
            return dict(ok=True,eax=0x13579bdf,eip=0x160,cs=0x50)
        if command == 'text':
            return dict(ok=True,mode=3,cols=1,rows=1,cursor=[0,0],chars=[self.text_chars],attrs=['07'])
        if command == 'screenshot':
            data = b'INVALID' if self.bad_png else png()
            return dict(ok=True,w=1,h=1,ms=self.ms,frames=self.frames,
                        png=base64.b64encode(data).decode(),private_path=str(self.root))
        if command.startswith('memr '):
            _, start, length, view, width = command.split()
            assert view == 'normal' and width == '1'
            return dict(ok=True,addr=int(start),data=bytes((int(start)+i)%251 for i in range(int(length))).hex())
        raise AssertionError('mutating/unexpected native command: '+command)

    def serve(self):
        while not self.stop.is_set():
            try:
                connection,_ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                with connection, connection.makefile('rb') as stream:
                    self.disconnected.clear()
                    connection.settimeout(10)
                    auth = stream.readline().decode().strip()
                    self.authentications += 1
                    if auth != 'auth '+self.token or self.failure == 'auth':
                        connection.sendall(json.dumps({'ok':False,'error':str(self.root)+' '+self.token}).encode()+b'\n')
                        continue
                    connection.sendall(b'{"ok":true,"auth":true}\n')
                    while not self.stop.is_set():
                        request = stream.readline()
                        if not request:
                            break
                        command = request.decode().strip()
                        self.commands.append(command)
                        if self.failure == 'eof':
                            break
                        if self.failure == 'timeout':
                            self.stop.wait(6)
                            break
                        if self.failure == 'json':
                            connection.sendall(b'{INVALID '+str(self.root).encode()+b'}\n')
                            break
                        reply = self.respond(command)
                        if self.after_command is not None:
                            self.after_command(command)
                        connection.sendall(json.dumps(reply).encode()+b'\n')
            except (OSError, ValueError):
                pass
            finally:
                self.disconnected.set()

    def close(self):
        self.stop.set()
        self.listener.close()
        self.thread.join(1)
        self.temp.cleanup()
