# Tootify

This project is in beta. It works quite well, but there are certainly some rough edges.

## Initial setup

Tootify is a simple Twitter/Instagram to Mastodon crossposter. To get it running, start with a `config.yaml`:

```
mastodon:
  access_token: <Mastodon access token>
  client_id: <Mastodon client id>
  client_secret: <Mastodon client secret>
  instance: <Mastodon instance>
twitter:
  bearer_token: <Twitter bearer token>
  username: <Twitter username>
  familiar_accounts:
    KonstantWeddige: weddige@gruene.social
  common_hashtags:
    '#servicetweet': '#servicepost'
```

The credentials for Mastodon can be filled in automatically:

```
> python -m tootify --login .\config.yaml
Mastodon instance: mastodon.tld
Email used to login: me@domain.tld
Password: ***
```

### Twitter

You will need to add your Twitter credentials manually. Go to <https://developer.twitter.com/> to create them.

The `familiar_accounts` and `common_hashtags` options allow you to define Twitter handles and hashtags that will be automatically mapped when crossposting.

Tootify will update the configuration file with the current synchronisation status. To update it without tooting anything, run `python -m tootify --skip config.yaml`. This will bring the configuration to the state where only new tweets are crossposted.

### Instagram

Instagram can be configured in a similar way to Twitter. Just add the following config section:

```
instagram:
  access_token: <Instagram Access Token>
  app_id: <Instagram Basic Display App ID>
  app_secret: <Instagram Basic Display App Secret>
  familiar_accounts:
    konstantinweddige: weddige@gruene.social
  common_hashtags:
    '#dogsofinstagram': '#fedidogs'
    '#catsofinstagram': '#fedicats'
```

To get the credentials, you will need to create an app for the Instagram Basic Display API at <https://developers.facebook.com/>. The access tokens can be generated using the *User Token Generator*. The app can stay in development mode indefinitely, so it doesn't need to be reviewed by Meta.

## Run it

Once everything is set up, you can run Tootify with `python -m tootify config.yaml`.

Tootify does not toot retweets or replies. It will however attempt to toot threads. This is a deliberate choice and will not change.

To automate the crossposter, you can schedule the call however you like. If you are using Azure, tootify comes with an [Azure Function](azure/README.md).
