import datetime
import logging
from pathlib import Path

import azure.functions as func
from tootify.tootifier import Tootifier


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info("The timer is past due!")

    tootifyer = Tootifier(Path("/tootify/config.yaml"))
    tootifyer.connect()
    tootifyer.toot_new_tweets()

    logging.info("Python timer trigger function ran at %s", utc_timestamp)
