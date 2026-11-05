# ROM setup for development builds of 86Box

The [official 86Box ROM repository](https://github.com/86Box/roms) recommends
**cloning** instead of downloading tagged ROM releases when using development
builds. The laboratory stores the checkout under the Windows interactive
user's supported search path: `%LOCALAPPDATA%\86Box\roms`.

**Licensing:** The upstream ROM repository states that files remain the
property of their respective copyright owners. This project does **not**
distribute those ROMs or include them in installation ISOs. Users must make
their own determination about obtaining and using ROMs in their jurisdiction.

## Automated setup is opt-in

Add `-Fetch86BoxROMs` to `Build-LabISO.ps1` to request first-login
retrieval after Git for Windows is installed. The ISO contains **only our
helper script**, not ROMs. The builder records this choice in
`*.iso.build.json` and stages `86box-roms-mode.txt`. Download failures
are logged to `C:\DeskMateLab\setup-logs\86box-roms-error.txt` but do not
invalidate the core toolchain installation. No ROM fetch happens by default.

After a successful clone, the script records the checked-out commit in
`C:\DeskMateLab\setup-logs\86box-roms-commit.txt`, so experimental results
can cite the exact ROM revision alongside
`86box-source-commit.txt`.

## Existing Windows 10 lab

Run as the **interactive lab account** in PowerShell, not LocalSystem:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\DeskMateLab\Setup-86Box-ROMs.ps1
```

The helper clones only if no existing ROM checkout is present. If it finds an
extracted ZIP or other nonempty directory without `.git`, it refuses to
overwrite it; manually rename the old folder first if you wish to switch.
An existing Git checkout is not updated automatically. To update to the
latest upstream ROM revision **explicitly**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\DeskMateLab\Setup-86Box-ROMs.ps1 -Update
```

The update requires a clean checkout and fast-forward; it does not reset
or delete local changes. Record both emulator and ROM commits when comparing
experiments. A new ROM set can affect machine selection and emulated behavior.

Reference: https://86box.readthedocs.io/en/latest/usage/roms.html
