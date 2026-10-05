import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    try:
        result = subprocess.run(
            [sys.executable, "-m", "src.entrypoint.voice"],
            cwd=project_root,
            check=False,
        )
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        sys.exit(130)
