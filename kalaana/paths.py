"""Where the data lives.

In a clone it is data/ next to the package. An installed wheel carries the committed data
(official directories, snapshot, labels, cached model readings) inside the package instead.
Set KALAANA_DATA_DIR to use another directory.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

_HERE: Final = Path(__file__).resolve().parent
_CLONE: Final = _HERE.parent / "data"


def _default() -> Path:
    return _CLONE if (_CLONE / "official").is_dir() else _HERE / "data"


DATA_DIR: Final = Path(os.getenv("KALAANA_DATA_DIR") or _default())
