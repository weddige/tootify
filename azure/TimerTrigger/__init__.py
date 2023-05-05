import logging
import os
from pathlib import Path

import azure.functions as func

from tootify.tootifier import Tootifier

logger = logging.getLogger(__name__)


def main(timer: func.TimerRequest) -> None:
    fails = 0
    config = os.environ.get("TOOTIFIER_CONFIG") or "/tootify/config.yaml"
    for path in config.split(":"):
        try:
            logger.info(f"Run tootifier {path}")
            tootifyer = Tootifier(Path(path))
            tootifyer.connect()
            tootifyer.toot()
        except Exception as e:
            logger.error(e)
            fails += 1
    if fails:
        raise RuntimeError("{fails} executions failed")
