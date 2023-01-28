import logging
import os
from pathlib import Path

import azure.functions as func

from tootify.tootifier import Tootifier

logger = logging.getLogger(__name__)


def main(timer: func.TimerRequest) -> None:
    try:
        config = os.environ.get("TOOTIFIER_CONFIG") or "/tootify/config.yaml"
        for path in config.split(":"):
            logger.info(f"Run tootifier {path}")
            tootifyer = Tootifier(Path(path))
            tootifyer.connect()
            tootifyer.toot()
    except Exception as e:
        logger.critical(e)
