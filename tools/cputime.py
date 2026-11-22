"""Run a command and report the CPU seconds it used, user + system.

Used by `make sample-cpu` inside the submission image to approximate the
board's CPU charge. It counts every descendant that was waited for, and the
last stderr line is `cputime: <seconds>`.

    python /cputime.py python -m selector
"""

import resource
import subprocess
import sys

status = subprocess.call(sys.argv[1:])
usage = resource.getrusage(resource.RUSAGE_CHILDREN)
print(f"cputime: {usage.ru_utime + usage.ru_stime:.6f}", file=sys.stderr)
sys.exit(status)
