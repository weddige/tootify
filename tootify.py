import argparse
import logging
import yaml
from tweepy import Client
from mastodon import Mastodon

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


def get_new_tweets(bearer_token, username, since_id=None):
    client = Client(bearer_token=bearer_token)
    user_id = client.get_user(username=username).data.id
    return client.get_users_tweets(
        id=user_id,
        exclude=["retweets", "replies"],
        # tweet_fields='created_at',
        since_id=since_id,
    ).data


def connect(instance, client_id, client_secret, access_token):
    api = Mastodon(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
        api_base_url=f"https://{instance}",
    )
    check = api.account_verify_credentials()
    if check.get("error"):
        logger.error(check.get("error"))
    else:
        username = str(check["username"])
        logger.info(f"connected on @{username}@{instance}")
    return api


def main():
    parser = argparse.ArgumentParser(prog="Tootify")
    parser.add_argument("status")
    parser.add_argument("--dry-run", action="store_true")
    add_verbosity_argument(parser)
    args = parser.parse_args()
    configure_logger(args)
    logger.debug(f"Load config '{args.status}'")
    status = yaml.load(open(args.status).read(), yaml.SafeLoader)

    tweets = get_new_tweets(
        status["twitter"]["bearer_token"],
        status["twitter"]["username"],
        status["twitter"].get("last_id", None),
    )

    if tweets:
        api = connect(
            instance=status["mastodon"]["instance"],
            client_id=status["mastodon"]["client_id"],
            client_secret=status["mastodon"]["client_secret"],
            access_token=status["mastodon"]["access_token"],
        )
        last_id = status["twitter"].get("last_id", None)
        for tweet in tweets:
            if args.dry_run:
                logger.info(f"Skip tweet {tweet.id}")
            else:
                logger.debug(f"Toot tweet {tweet.id}")
                api.toot(tweet.text)
            last_id = max(last_id, tweet.id)
        status["twitter"]["last_id"] = last_id
        yaml.dump(status, open(args.status, "w"), yaml.dumper.SafeDumper)
    else:
        logger.warning("No new tweets.")


if __name__ == "__main__":
    main()
