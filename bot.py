from datetime import datetime, time
from flask import Flask, request
from html import unescape
from urllib.parse import urlparse
import telegram
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as pyplot
import requests
import random
import MySQLdb
import atexit
import re

app = Flask(__name__)


class ImageContent:
    def __init__(self, type, content, caption=None):
        self.type = type
        self.content = content
        self.caption = caption


class User:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class ImageService:

    # String constants
    BOT_URL = '[BOT_URL_HERE]'
    TOKEN = '[TOKEN_HERE]'
    CERT_PATH = '[CERT_PATH_HERE]'
    START_TEXT = "[START_TEXT_HERE]"
    HELP_TEXT = """A list of available commands:
                /picture: sends a picture
                /gif: sends a gif
                [COMMANDS_HERE]
                /help - Shows this help."""


    # Built-in subreddits
    all_subs = ['pics', 'gifs'] # Add subreddits here
    commands_to_subs = {'picture': 'pics', 'gif': 'gifs'} # Add commmands (-> subreddits) here

    def __init__(self):
        self.bot = telegram.Bot(token=self.TOKEN)
        self.stats_service = StatsService()
        self.cached_posts = []

    def check_if_allowed(self, user):
        stats = self.stats_service.get_user_stats(user)
        format = '%Y-%m-%d %H:%M:%S'
        if len(stats) > 0:
            last_time = stats[0][3]
            current_time = datetime.now()
            if last_time is not None:
                timedelta = current_time - last_time
                if timedelta.total_seconds() < 20:
                    return 'Don\'t spam please!'
        return True

    def get_post(self, sub):
        if len(self.cached_posts) == 0:
            r = requests.get('https://www.reddit.com/r/' + sub + '.json?count=10',
                             headers={'User-agent': 'TRIS'}).json()
            self.cached_posts = [post if post['kind'] == 't3' else None for post in r['data']['children']]

        return self.cached_posts.pop(random.randint(0, len(self.cached_posts)))

    def get_image(self, sub):
        post = self.get_post(sub)
        url = urlparse(post['data']['url'])
        domain = url.hostname
        image_url = None
        content_type = 'photo'

        if 'gfycat.com' in domain:
            gif_id = url.path.split('/')[-1]
            image_url = requests.get('https://api.gfycat.com/v1test/gfycats/' + gif_id).json()['gfyItem']['mobileUrl']
            content_type = 'video'

        elif 'imgur.com' in domain:
            slash_split = url.path.split('/')
            point_split = url.path.split('.')
            if domain.split('.')[0] == 'i':
                if point_split[-1] == 'gifv':
                    content_type = 'video'
                    image_url = url.geturl().rsplit('.')[0] + '.mp4'
                else:
                    image_url = url.geturl()
            elif slash_split[1] != 'a':
                image_url = 'https://i.imgur.com/' + slash_split[-1] + '.jpg'

        elif 'reddituploads.com' in domain:
            image_url = url.geturl()

        else:
            return None

        print(image_url)
        print(post['data']['title'])
        return ImageContent(content_type, unescape(image_url), unescape(post['data']['title']))

    def get_image(self, user, sub):
        status = self.check_if_allowed(user)
        if status:
            image_content = None
            while image_content is None:
                image_content = self.get_image(sub)
                if len(self.cached_posts) == 0:
                    break
            self.cached_posts.clear()
            return image_content
        else:
            return ImageContent('message', status)

    def get_random_image(self, user):
        return self.get_image(user, random.choice(self.all_subs))

    def send_text(self, user, message):
        self.bot.send_message(chat_id=user.id, text=message)

    def send_image(self, user, photo, caption=None):
        self.bot.send_photo(chat_id=user.id, photo=photo, caption=caption)

    def send_video(self, user, video, caption):
        self.bot.send_video(chat_id=user.id, video=video, caption=caption)

    def send_image(self, user, image_content):
        if image_content is not None:
            if image_content.type == 'photo':
                self.send_image(user, image_content.content, image_content.caption)
                self.stats_service.log_query(user)
            elif image_content.type == 'video':
                self.send_video(user, image_content.content, image_content.caption)
                self.stats_service.log_query(user)
            elif image_content.type == 'message':
                self.send_text(user, image_content.content)
        else:
            self.send_text(user, 'Sorry, I could not even find one image :(')

    def send_stats(self, user):
        self.stats_service.get_graph().savefig('test.png')
        self.send_image(user, open('test.png', 'rb'))

    def rate(self, from_id):
        pass


class StatsService:

    def __init__(self):
        self.db = MySQLdb.connect(host='localhost', user='TRIS', passwd='[PASSWORD]', db='stats')
        self.cur = self.db.cursor()
        atexit.register(self.exit_handler)

    def log_query(self, user):
        dt = datetime.now()
        format = '%Y-%m-%d %H:%M:%S'
        if self.get_user_stats(user) is not None:
            self.cur.execute('UPDATE usercount SET count = count + 1, last_query = %s WHERE id = %s',
                             (dt.strftime(format), user.id))
        else:
            self.cur.execute('INSERT INTO usercount(id, name, count) VALUES(%s, %s, %s, %s)',
                             (user.id, user.name, 1, dt.strftime(format)))

    def get_user_stats(self, user):
        self.cur.execute('SELECT * FROM usercount WHERE id = %s', (user.id,))
        return self.cur.fetchall()

    def get_full_stats(self):
        self.cur.execute('SELECT * FROM usercount ORDER BY count DESC')
        return self.cur.fetchall()

    def get_graph(self):
        stats = self.get_full_stats()
        data = [d[2] for d in stats]
        labels = [l[1] for l in stats]
        pyplot.xkcd()
        pyplot.title('Requests per users')
        pyplot.xlabel('Users')
        pyplot.ylabel('Number of requests')
        pyplot.bar(range(len(data)), data, align='center')
        pyplot.xticks(range(len(labels)), labels)
        pyplot.tight_layout()
        diff = data[0] - data[1]
        if diff >= data[0] / 2 and diff >= 8:
            pyplot.annotate('Spammer!', xy=(0, data[0]), arrowprops=dict(arrowstyle='->'),
                            xytext=(1, data[0] - 4))
        return pyplot

    def exit_handler(self):
        if self.db is not None:
            self.db.close()


@app.route('/TRIS/update', methods=['POST'])
def update():
    if request.headers['Content-Type'] == 'application/json':
        print(request.get_json())
        data = request.get_json()
        from_id = data['message']['from']['id']
        name = data['message']['from']['first_name']
        text = data['message']['text']
        user = User(from_id, name)

        if text[0] == '/':
            text = text[1:]

            if text == 'start':
                imgsrv.send_text(user, imgsrv.START_TEXT.format(name))

            elif text == 'help':
                imgsrv.send_text(user, re.sub(' +', ' ', imgsrv.HELP_TEXT))

            elif text == 'random':
                imgsrv.send_image(user, imgsrv.get_random_image(user))

            elif text == 'rate':
                imgsrv.rate(user)

            elif text == 'stats':
                imgsrv.send_stats(user)

            elif 'custom:' in text:
                imgsrv.send_image(user, imgsrv.get_image(user, text.split(':')[1]))

            elif text in imgsrv.commands_to_subs:
                imgsrv.send_image(user, imgsrv.get_image(user, imgsrv.commands_to_subs[text]))

            else:
                imgsrv.send_text(user, 'I don\'t know that command')
        else:
            imgsrv.send_text(user, 'I only speak with /slashes')

    return 'OK'


if __name__ == "__main__":
    print("TRIS started...")
    ps = ImageService()
    context = (imgsrv.CERT_PATH + 'fullchain.pem', imgsrv.CERT_PATH + 'privkey.pem')
    app.run(host='0.0.0.0', port=8443, ssl_context=context)
