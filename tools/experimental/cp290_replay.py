"""Replay the observed DeskMate CP290 subset entirely in memory."""

import argparse
import json


HOUSE_CODES = 'MECKOGAINFDLPHBJ'
TRANSMIT_SYNC = b'\xff' * 16
RECEIVE_SYNC = b'\xff' * 6
STATUS_OK = RECEIVE_SYNC + b'\x01'


class VirtualCP290:
    """A fixed clock, one timer slot, and simulated units."""

    def __init__(self):
        self.base = 0x60
        self.clock = bytes((44, 21, 4))
        self.timer = None
        self.units = {}

    def command(self, frame):
        if not frame.startswith(TRANSMIT_SYNC):
            raise ValueError('Expected sixteen synchronization bytes')
        command = frame[len(TRANSMIT_SYNC):]
        if len(command) == 2 and command[0] == 0 and command[1] & 0x0f == 0:
            self.base = command[1]
            self.timer = None
            self.units.clear()
            return {'operation': 'set-house-code', 'house': HOUSE_CODES[self.base >> 4]}, (STATUS_OK,)
        if command == b'\x04':
            clock = self.clock + bytes((self.base,))
            return {'operation': 'get-clock'}, (STATUS_OK + clock + bytes((sum(clock) & 0xff,)),)
        if command == b'\x05':
            first = self.timer or b'\xff'
            checksum = sum(self.timer or b'') & 0xff
            return {'operation': 'get-timers'}, (STATUS_OK + first + b'\xff' * 127 + bytes((checksum,)),)
        if len(command) == 12 and command[:3] == b'\x03\x00\x00':
            payload = command[3:-1]
            if sum(payload) & 0xff != command[-1]:
                raise ValueError('Timer command checksum mismatch')
            self.timer = payload if payload[0] else None
            return {'operation': 'write-timer', 'slot': 0, 'payload': payload.hex()}, (STATUS_OK,)
        if len(command) != 6 or command[0] != 1:
            raise ValueError('Unsupported or incomplete CP290 command')

        _, action, house, upper_units, lower_units, checksum = command
        if sum(command[1:-1]) & 0xff != checksum:
            raise ValueError('Direct command checksum mismatch')
        if action not in (2, 3) or house & 0x0f or not (upper_units or lower_units):
            raise ValueError('Expected Direct On or Off, a house code, and selected units')

        address = HOUSE_CODES[house >> 4]
        selected = [
            first + bit for first, mask in ((1, lower_units), (9, upper_units))
            for bit in range(8) if mask & (0x80 >> bit)
        ]
        for unit in selected:
            self.units[address, unit] = action == 2
        completion = bytes((house | action, upper_units, lower_units, self.base))
        event = {'operation': 'on' if action == 2 else 'off', 'house': address, 'units': selected}
        return event, (STATUS_OK, STATUS_OK + completion + bytes((sum(completion) & 0xff,)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frames', nargs='+', help='One complete hex frame per argument')
    args = parser.parse_args()
    controller = VirtualCP290()
    for frame in args.frames:
        try:
            event, replies = controller.command(bytes.fromhex(frame))
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps({'event': event, 'replies': [reply.hex() for reply in replies]}))


if __name__ == '__main__':
    main()
