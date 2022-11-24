import argparse
import logging
from pathlib import Path

from tootify.tootifier import Tootifier

from .cli import add_verbosity_argument, configure_logger

logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser(prog="Tootify")
parser.add_argument("status", type=Path)
parser.add_argument("--dry-run", action="store_true", help="Skip everything for debugging")
parser.add_argument("--skip", action="store_true", help="Skip tweeting (but update config)")
add_verbosity_argument(parser)
args = parser.parse_args()
configure_logger(args)

tootifyer = Tootifier(args.status)
tootifyer.connect()
tootifyer.toot_new_tweets(dry_run=args.dry_run)
