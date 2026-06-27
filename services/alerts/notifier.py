import subprocess
import sys


def notify(title: str, body: str) -> None:
    if sys.platform != "darwin":
        return
    try:
        script = f'display notification "{body}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False, timeout=5)
    except Exception:
        pass
