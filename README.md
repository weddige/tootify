# Tootify

This project is in early alpha state.

Tootify is a simple Twitter to Mastodon chrossposter. To get it running, create `config.yaml` with the credentials:

```
mastodon:
  access_token: <Mastodon access token>
  client_id: <Mastodon client id>
  client_secret: <Mastodon client secret>
  instance: <Mastodon instance>
twitter:
  bearer_token: <Twitter bearer token>
  username: <Twitter username>
```

Tootify will update this file with the current syncronisation status. To update it without tooting any tweets run `python -m tootify --skip config.yaml`.

After that it can be run with `python -m tootify config.yaml`.

Tootify does not toot any retweets or replies. However it tries to toot threads.