import argparse
import logging
from pathlib import Path

from tootify.tootifyer import Tootifyer

from .cli import add_verbosity_argument, configure_logger

logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser(prog="Tootify")
parser.add_argument("status", type=Path)
parser.add_argument("--dry-run", action="store_true")
add_verbosity_argument(parser)
args = parser.parse_args()
configure_logger(args)

tootifyer = Tootifyer(args.status)
tootifyer.read()
tootifyer.connect()
tootifyer.toot_new_tweets(dry_run=args.dry_run)
tootifyer.write()
