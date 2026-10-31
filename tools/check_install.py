"""Run against the installed wheel, with no src path injection."""
from pathlib import Path
import importlib.metadata,subprocess,sys,sysconfig
import deskmate_formats.calendar.personal as personal
from deskmate_formats.calendar.writer import Appointment,capacity
assert personal.FILE_SIZE==6144 and Appointment and callable(capacity)
dist=importlib.metadata.distribution('deskmate-formats')
assert dist.version=='0.1.0.dev0'
for command in ('deskmate-calendar','deskmate-calendar-append'):
    matches=[e for e in dist.entry_points if e.name==command]
    assert len(matches)==1 and callable(matches[0].load())
    executable=Path(sysconfig.get_path('scripts'))/(command+('.exe' if sys.platform=='win32' else ''))
    subprocess.run([str(executable),'--help'],check=True,stdout=subprocess.DEVNULL)
print('Installed package imports and both CLI entry points passed',sys.version.split()[0])
