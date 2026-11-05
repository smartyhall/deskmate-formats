"""Synthetic controls for original code bytes, FAT12 layout and RAM mapping."""
import copy
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('canary',
    Path(__file__).resolve().parents[2] / 'tools/experimental/guest_canary.py')
canary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(canary)


def synthetic():
    segment = 0x1234
    regs = dict(canary.REGISTERS, cs=segment, ds=segment, es=segment, ss=segment,
                cs_base=0x12340, ds_base=0x12340, es_base=0x12340, ss_base=0x12340,
                cr0=0x10, eflags=0x46, eip=0x160)
    return {'registers': regs, 'memory': [
        {'address': 0x12440, 'data': canary.program()[:98].hex()},
        {'address': 0x12540, 'data': canary.DATA.hex()}],
        'text': {'lines': [line.ljust(80) for line in canary.LINES] + [' '*80]*20},
        'status': dict(ms=1000, frames=70, held=True, paused=False, bios_mode=3, w=720, h=400),
        'info': dict(version='SYNTHETIC', machine='SYNTHETIC', hard_resets=1,
                     soft_resets=1, last_reset_ms=0)}


class CanaryTests(unittest.TestCase):
    def test_instruction_oracle_and_fixed_layout(self):
        data = canary.program()
        self.assertEqual(len(data), 288)
        self.assertEqual(data[:23], bytes.fromhex('0e1fb80300cd10ba8001b409cd21fa8cc88ed88ec08ed0'))
        # Independently specified little-endian immediate encodings, x86 register order.
        expected = bytes.fromhex(
            '66b8df9b5713 66b90df0ad0b 66bacc33aa55 66bbe0ac6824 '
            '66bc00ff0000 66bd40302010 66be44332211 66bf88776655')
        self.assertEqual(data[23:71], expected)
        self.assertEqual(data[71:96], b'\x90'*25)
        self.assertEqual(data[96:98], b'\xeb\xfe')
        self.assertEqual(0x162 + struct.unpack('b', data[97:98])[0], 0x160)
        self.assertEqual(data[128:128+len(canary.BANNER)], canary.BANNER)
        self.assertEqual(data[256:], bytes.fromhex(
            '444d462d43414e4152592d763100000102030405060708090a0b0c0d0e0fa55a'))

    def test_independent_fat12_file_recovery(self):
        image = canary.floppy(canary.program())
        self.assertEqual(len(image), 1474560)
        self.assertEqual(image[510:512], b'\x55\xaa')
        self.assertEqual(image[512:5120], image[5120:9728])
        fat = image[512:5120]
        self.assertEqual((int.from_bytes(fat[3:5], 'little') & 0xfff), 0xfff)
        directory = image[19*512:33*512]
        self.assertEqual(directory[32:43], b'CANARY  COM')
        cluster = int.from_bytes(directory[58:60], 'little')
        size = int.from_bytes(directory[60:64], 'little')
        offset = (33 + cluster - 2) * 512
        self.assertEqual(image[offset:offset+size], canary.program())
        self.assertEqual(image[62:66], b'\xfa\xf4\xeb\xfd')

    def test_floppy_rejects_empty_or_multicluster_payload(self):
        for data in (b'', bytes(513), 'not bytes'):
            with self.assertRaises(ValueError):
                canary.floppy(data)

    def test_real_mode_mapping_and_sanitized_validation(self):
        result = canary.validate(synthetic())
        self.assertEqual(result['locations']['checkpoint'], 0x124a0)
        self.assertEqual(result['locations']['data'], 0x12540)
        self.assertEqual(result['data_bytes_verified'], 32)
        self.assertEqual(result['code_bytes_verified'], 98)
        self.assertNotIn('memory', result)

    def test_wrong_register_segment_base_mode_and_checkpoint_rejected(self):
        for name, value in (('eax',0), ('cs',0xa000), ('ds',0x4321), ('cs_base',0),
                            ('cr0',1), ('eip',0x162), ('eflags',0x246)):
            observation = synthetic()
            observation['registers'][name] = value
            with self.subTest(field=name), self.assertRaises(ValueError):
                canary.validate(observation)

    def test_changed_or_truncated_code_data_and_wrong_text_rejected(self):
        original = synthetic()
        for index in (0,1):
            observation = copy.deepcopy(original)
            observation['memory'][index]['data'] = '00'
            with self.assertRaises(ValueError):
                canary.validate(observation)
        observation = copy.deepcopy(original)
        observation['text']['lines'][0] = 'not the canary'
        with self.assertRaises(ValueError):
            canary.validate(observation)

    def test_generation_is_external_exclusive_and_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'new'
            first = canary.generate(output)
            with self.assertRaises(FileExistsError):
                canary.generate(output)
            second = canary.generate(Path(temp)/'other')
            self.assertEqual(first, second)
        with self.assertRaises(ValueError):
            canary.generate(canary.ROOT/'must-not-create-binaries')


if __name__ == '__main__':
    unittest.main()
