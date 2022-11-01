import argparse
import logging
from collections import defaultdict
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
        tweet_fields=["conversation_id", "referenced_tweets"],
        since_id=since_id,
    ).data


def get_conversations(tweets):
    conversations = defaultdict(list)
    for tweet in tweets:
        conversations[tweet.conversation_id].append(tweet)
    return dict(conversations)


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
        conversations = get_conversations(tweets)
        api = connect(
            instance=status["mastodon"]["instance"],
            client_id=status["mastodon"]["client_id"],
            client_secret=status["mastodon"]["client_secret"],
            access_token=status["mastodon"]["access_token"],
        )
        last_id = status["twitter"].get("last_id", None)
        for conversation in get_conversations(tweets).values():
            references = {}
            for tweet in sorted(conversation, key=lambda tweet: tweet.id):
                if tweet.id == tweet.conversation_id:
                    if args.dry_run:
                        logger.info(f"Skip tweet {tweet.id}")
                    else:
                        logger.debug(f"Toot tweet {tweet.id}")
                        toot = api.toot(tweet.text)
                else:
                    replied_to = (
                        [
                            ref.id
                            for ref in tweet.referenced_tweets or []
                            if ref.type == "replied_to"
                        ]
                        or [None]
                    )[0]
                    if replied_to in references:
                        if args.dry_run:
                            logger.info(f"Skip reply {tweet.id} to {replied_to}")
                        else:
                            logger.debug(f"Toot reply {tweet.id} to {replied_to}")
                            toot = api.status_post(
                                tweet.text, in_reply_to_id=references[replied_to]
                            )
                    else:
                        logger.error(
                            f"Skip {tweet.id}. Did not find referenced tweet {replied_to}"
                        )
                if not args.dry_run:
                    references[tweet.id] = toot["id"]
                last_id = max(last_id, tweet.id) if last_id else tweet.id
        status["twitter"]["last_id"] = last_id
        yaml.dump(status, open(args.status, "w"), yaml.dumper.SafeDumper)
    else:
        logger.warning("No new tweets.")


if __name__ == "__main__":
    main()
