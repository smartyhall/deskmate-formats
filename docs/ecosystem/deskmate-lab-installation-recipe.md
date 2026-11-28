# Laboratory installation recipe

This recipe describes how the atlas installations were prepared so a later
session can reproduce an environment without repeating the investigation. It
records method and identities, not commercial bytes: installation media,
disk images, and installed trees stay outside Git.

## What you need

- The private TVDog mirror with its `originals` tree and settled transfer
  receipts, or another source with recorded identities.
- The 86Box automation build and its pinned ROM revision.
- The Python transport and launcher in `tools/`: `86box_launch.py` and
  `86box_client.py`.
- Free space for one disposable disk image per simultaneous experiment. One
  active emulator instance per campaign, on its own automation port.

## Prepare the media

Reconstruct FAT12 working disks from verified file sets:

```text
python tools/experimental/deskmate_install_media.py 303 <originals> <output>
python tools/experimental/deskmate_install_media.py 305 <originals> <output>
```

The tool checks every ZIP against
[the media manifest](../ecosystem/deskmate-installation-media.json), preserves
member bytes and DOS timestamps, and refuses to overwrite an existing image.
Reconstructed images are working media with synthetic volume serials; they
are not factory disks. Record each image hash in the experiment receipt.

Raw preservation images need no reconstruction. Verify their hashes against
the manifest or the source receipt instead.

## Prepare the machine

Copy, never move, a verified DOS baseline:

```text
cp <baseline>/86box.cfg        <campaign-machine>/86box.cfg
cp <baseline>/nvr/*            <campaign-machine>/nvr/
cp <baseline>/<disk>.img       <campaign-machine>/<campaign>.img
```

Point `hdd_01_fn` in the copied configuration at the copied image. Never
edit the sealed baseline, and never reuse another campaign's machine
directory. Record the baseline hash before and after the copy; they must
match.

## Launch

```text
python tools/86box_launch.py --machine <campaign-machine> --port <free port>
```

The launcher starts a visible window, waits for an authenticated held state
at 0 ms, and writes a private launch receipt. Do not click the emulated
display and do not inject host input; every guest action goes through the
socket. If another campaign's emulator is already running, choose a
different machine and port rather than attaching to it.

## Drive the installer

The machine is held, so time advances only in explicit steps. Two client
behaviors matter:

- `step` accepts 1 to 1000 ms. Use `advance <ms>` for repeated 1000 ms steps.
- `type` sends US-layout scancodes. Pace text with `--pace-ms` when a burst
  risks dropped characters, and send Enter separately with `tap 0x1c`.

A workable loop for each disk is: mount the image with `floppy 0 <path>`,
advance until the numbered request appears, press Enter once, and advance
again. Capture a frame at each prompt, then keep the frames as an ordered
private sequence. The numbered requests in the 3.05 nine-set follow the
shipped labels, but the printer phase reads `.ACC` files again from Disk 6
and later asks for Disks 7 and 9, so a single ascending pass is not enough.

Practical rules learned from the runs:

- Mount media only after the installer asks for it.
- Never swap media during a copy. A premature swap produces an insert
  prompt; mount the disk containing the named file and choose RETRY.
- Verify the destination default by reading the dialog rather than assuming
  it; the nine-ZIP lineage opens with an empty field.
- After the reset, confirm the version with `VER` before launching DeskMate.

## Record the result

For each installation, retain privately: launch receipt and process
identity, configuration and NVRAM hashes, media image hashes, every captured
frame in order, the stopped disk hash, the complete installed-file manifest,
and the sampled emulated timestamps. Publish only the sanitized receipt in
`docs/evidence/` and the reviewed captures that the image manifest lists.

Update the [installation registry](../ecosystem/deskmate-installation-registry.json)
with the release state and the environment identity. A new environment gets
its own entry; do not reuse an existing identifier for a different machine
configuration.
