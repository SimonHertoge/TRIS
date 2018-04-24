# TRIS

TRIS - *Telegram Reddit Image Service* - is a webhooks bot for Telegram which delivers images and gifs from imgur, reddituploads, and gfycat as a response to (custom) commands. Subreddits can be customized in the script or chosen by the user. Also included is a simple rate limiter and stats manager, which can send a graph of number of requests by user.

## Setup

1. Install all dependencies with `pip install -r requirements.txt`.
2. Set up a MySQL database 'stats'.
3. Customize the string constants (url, token, ...) with your bot credentials.
4. Possibly change subreddits in `all_subs` and `commands_to_subs`.
5. Run the bot with `python bot.py`.

For more information about how to set up a bot, see the official documentation:
https://core.telegram.org/bots/
https://core.telegram.org/bots/webhooks
https://core.telegram.org/api
