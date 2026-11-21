"""Write the original HDS controls for the MidiMapper 6.38 differentials."""

import argparse
from pathlib import Path


def _control(name, rows, bpm=100):
    header = ['[Song]', f'Name={name}', 'Beats Per Measure=4', 'Single Beat Note=4',
              f'Pace={bpm}', 'PolyDur=True', '', '[Notes]']
    return '\r\n'.join([*header, *rows, '']).encode('ascii')


def controls():
    pitch = 'C3 C+3 C-3 C++3 C--3 C+++3 C---3 C1 C2 C4 C C+ C- c#3 Db3 B#3 Cb3 E#3 Fb3 A-3 a-3'
    timing = '4C3 4C3 4R 2D3 8.E3 16F3 32G3 T8A3 T8B3 T8C+3 4..C3'
    enharmonic = 'D#3 Eb3 F#3 Gb3 G#3 Ab3 A#3 Bb3 B#-3 Cb+3 C----3 C-----3 G+++++3 C99'
    result = {
        'PITCH.HDS': _control('Pitch spelling control', [f'8{note}/x/x' for note in pitch.split()], 120),
        'ENHARM.HDS': _control('Enharmonic and boundary control',
                               [f'8{note}/x/x' for note in enharmonic.split()], 120),
        'CHANNEL.HDS': _control('Channel and program control', [
            '[Inst. 1 = 41]', '[Inst. 2 = 74]', '[Inst. 1 dyn. = pp]', '[Inst. 2 dyn. = ff]',
            '2C3/4E3/4R', 'x/4G3/x', '[Midi 192 11 0]', '[Midi 193 73 0]', '4D3/4F3/4R',
        ]),
        'STRUCT.HDS': _control('Structure probe', [
            '[Time 6/8]', '[Key sig=G]', '[Bar 1]', '[Score marker A]', '[Repeat 2x]',
            'Sb4C3/x/x', 'Se4C3/x/x', '[Ending 1]', 'Sb8E3/x/x', 'Se8F3/x/x',
            '[Ending 2]', 'Lb8G3/x/x', 'Le8A3/x/x', '[Repeat End]', '[Tempo= 1/8 = 120]', '4G3/x/x',
        ]),
    }
    for bpm in (60, 100, 180):
        result[f'T{bpm}.HDS'] = _control(f'Timing at {bpm}', [f'{note}/x/x' for note in timing.split()], bpm)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='new directory for the DOS-named HDS controls')
    args = parser.parse_args()
    args.output.mkdir()
    for name, data in controls().items():
        with (args.output / name).open('xb') as handle:
            handle.write(data)


if __name__ == '__main__':
    main()
