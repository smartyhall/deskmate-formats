# Reproduce the 86Box PSSJ DAC capture

The successful run used a disposable Tandy 1000 RSX with a 25 MHz 386SX,
4 MiB RAM, internal VGA and PSSJ, DOS 5.00, DeskMate 3.05.00 runtime and
RSX OEM Sound and Music modules. The ROM and application identities are in
the [native evidence receipt](../evidence/audio-native-20261118.json).

## Build and replay

1. Locate the existing private `audio-native-20261118` archive. Use the
   86Box source revision `855258da966f1594f568350be59e8e1eca082ed1`
   in a disposable worktree. Run `git apply --check` on the retained
   `86box-pssj-tap.diff`, then apply it to that worktree. The reverse check
   succeeds on the retained instrumented worktree at that revision.
2. Use MSYS2 UCRT64, Ninja and the native automation build option. The
   retained configure/build logs and CMake cache record the original build.

   ```powershell
   $env:Path = 'C:\msys64\ucrt64\bin;' + $env:Path
   $env:MSYSTEM_PREFIX = 'C:/msys64/ucrt64'
   cmake -S $tapSource -B $tapBuild -G Ninja -DAUTOMATION=ON -DCMAKE_BUILD_TYPE=Release -DUSE_QT6=OFF
   cmake --build $tapBuild --parallel 6
   ```

3. Use `playback-tap.py` to prepare a disposable machine from the stopped
   follow-up disk and `tap-probes.py` for the scratch data floppy. Keep the
   original disk, config and NVRAM. Set `DESKMATE_RESEARCH_PSSJ_CAPTURE` to a
   new raw file. The tap opens it exclusively and captures at most 96 seconds.
   The original visible launch used seed 1 and its authenticated loopback
   automation socket. Boot to DOS before attaching the data floppy. The
   pre-boot attachment attempt did not reach DOS.
4. Follow the private `tap-run/operate.py` and its saved transition receipts.
   For a small fresh check, play the synthetic Sound tone and one Music
   score using the same sample in two octaves. Stop and close the emulator
   through its socket before reading the capture. Preserve the selected
   playback boundaries and the stopped capture's hash and sample count.

86Box provides the `COPYING` notice for GPL version 2 at the pinned tree.
The private patch modifies its PSSJ source. Any downstream publication of
the patch needs to retain the applicable upstream terms and notices, separately
from the license of the independent Python analyzer.

## Analyze the stopped capture

```powershell
python tools/experimental/pssj_capture.py $raw sound:30.52:31.22 octave:39.17:40.31
```

The analyzer reads mono signed 16-bit little-endian PCM at 48 kHz. It detects
10 ms blocks with peak-to-peak excursion above 25, requires two consecutive
active blocks, and estimates a periodic tone from rising mean crossings.
Unstable windows return no frequency. The approach estimates clean tones;
the archived NumPy method uses a spectral peak and can characterize other
signals differently. All reported intervals refer to emulated sample time.

Reanalysis of the retained 95.08-second stream reproduced the recorded
Sound onset at 30.62 seconds and its 0.50-second duration, with a 448.60 Hz
median. The Music octave probe began at 39.27 and 39.84 seconds, measuring
0.42 and 0.37 seconds with medians of 444.44 and 888.89 Hz.
The repeat probe produced four activity intervals at 74.49, 75.06, 75.63
and 76.20 seconds. Synthetic tests cover silence, onset, duration, frequency
and incomplete frames. These checks used the retained capture and synthetic
input. A fresh native run and build were not performed.

The tap writes the PSSJ DAC's mono contribution in `pssj_get_buffer` before
addition to the mixer. It excludes the SN76489 PSG path and other emulator
devices, any host resampling or recording path, speakers and room acoustics.
The original VM had zero WinMM endpoints, so the evidence concerns guest
sequencing and DAC output.

## Private inventory verified against retained bytes

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Source diff | 1,640 | `20c1d526f42fc8345ae1a7df2e56c078534131eea31e825f9408b741ed4db174` |
| Instrumented executable | 70,905,409 | `348df44531bea6ab349a487af6b7e46171b9b90652448ad5816d5a9c6301ce59` |
| Scratch floppy | 1,474,560 | `a856d9dbeae8698f9aae2a03dbd566c7783f751cce0648fdda4eb0acd26969bb` |
| Stopped DAC stream | 9,127,680 | `13ff8ed509df0ffe2efad192725a7913e33fc802a48ca8e09c5ad731b2216369` |
