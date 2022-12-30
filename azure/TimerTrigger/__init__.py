import datetime
import logging
from pathlib import Path

import azure.functions as func
from tootify.tootifier import Tootifier


def main(mytimer: func.TimerRequest) -> None:
    tootifyer = Tootifier(Path("/tootify/config.yaml"))
    tootifyer.connect()
    tootifyer.toot()
