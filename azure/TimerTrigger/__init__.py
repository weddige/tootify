import logging
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import azure.functions as func
from azure.storage.fileshare import ShareFileClient

from tootify.tootifier import Tootifier

logger = logging.getLogger(__name__)


@contextmanager
def shared_file(conn_str, share_name, file_name):
    with TemporaryDirectory() as tmp_dir:
        logger.debug(f"Created tmp dir {tmp_dir}")
        file_client = ShareFileClient.from_connection_string(conn_str, share_name, file_name)
        remote_path = Path(file_name)
        local_path = Path(tmp_dir).joinpath(remote_path.name)
        with open(local_path, "wb") as data:
            logger.debug(f"Download {local_path}")
            stream = file_client.download_file()
            data.write(stream.readall())
        yield local_path
        with open(local_path, "rb") as source_file:
            data = source_file.read()
            logger.debug(f"Upload {local_path}")
            file_client.upload_file(data)


def main(timer: func.TimerRequest) -> None:
    fails = 0
    logger.info(":".join(map(str, Path("/").iterdir())))
    config = os.environ.get("TOOTIFIER_CONFIG") or "config.yaml"
    connection_string = os.environ.get("WEBSITE_CONTENTAZUREFILECONNECTIONSTRING")
    share_name = os.environ.get("WEBSITE_CONTENTSHARE")
    logger.info(f"CONFIG: {config}")
    for path in config.split(":"):
        try:
            logger.info(f"Run tootifier {path}")
            with shared_file(connection_string, share_name, path) as config:
                tootifyer = Tootifier(config)
                tootifyer.connect()
                tootifyer.toot()
        except Exception as e:
            logger.error(e)
            fails += 1
    if fails:
        raise RuntimeError(f"{fails} executions failed")
