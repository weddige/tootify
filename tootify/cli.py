import argparse
import logging

logger = logging.getLogger(__name__)


def add_verbosity_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--verbose", "-v", action="count", default=0)


def configure_logger(args: argparse.Namespace) -> None:
    level = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }[min(args.verbose, 2)]

    logging.basicConfig(level=level)

    logger.debug(f"Set log level {level}")
