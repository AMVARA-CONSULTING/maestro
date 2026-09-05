from __future__ import annotations

import logging
import sys

from maestro.bot import run_bot
from maestro.settings import load_settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    settings = load_settings()
    run_bot(settings)


if __name__ == "__main__":
    main()
