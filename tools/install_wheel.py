"""Install exactly one newly built wheel without shell-specific wildcards."""
from pathlib import Path
import subprocess,sys
wheels=list(Path('dist').glob('*.whl'))
if len(wheels)!=1:raise SystemExit('Expected exactly one wheel in dist')
subprocess.run([sys.executable,'-m','pip','install','--force-reinstall','--no-deps',str(wheels[0])],check=True)
