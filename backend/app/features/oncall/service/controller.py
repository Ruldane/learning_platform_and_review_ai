"""The diagnostic's two processes, both started in the existing sandbox."""

from app.features.oncall.scenarios import SIZES

ENTRY = "diagnostic.py"
WORKER = "diagnostic_worker.py"
_CASES = str(list(SIZES))

CONTROLLER = f"""import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    worker = Path(__file__).with_name({WORKER!r})
    reader, writer = os.pipe()
    with os.fdopen(reader, "rb") as channel:
        try:
            child = subprocess.Popen(
                [sys.executable, str(worker), str(writer), {_CASES!r}],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                pass_fds=(writer,),
            )
        finally:
            os.close(writer)
        message = channel.read(4097)
    if child.wait() != 0 or len(message) > 4096:
        raise SystemExit(1)
    print(json.dumps({{"checks": json.loads(message)}}))


if __name__ == "__main__":
    main()
"""

SERVICE_WORKER = """import json
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def main():
    channel = int(sys.argv[1])
    os.set_inheritable(channel, False)
    cases = json.loads(sys.argv[2])
    project = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project))
    spec = spec_from_file_location("service", project / "service.py")
    service = module_from_spec(spec)
    sys.modules[spec.name] = service
    spec.loader.exec_module(service)

    results = [service.serve(size, incident_active=True) for size in cases]
    with os.fdopen(channel, "w") as output:
        json.dump(results, output)


if __name__ == "__main__":
    main()
"""
