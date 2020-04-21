import time
import praw
import prawcore 
import requests
import logging
import Config
from bs4 import BeautifulSoup
responded = 0
footer = ""
reddit = praw.Reddit(client_id=Config.cid,
                     client_secret=Config.secret,
                     password=Config.password,
                     user_agent=Config.agent,
                     username=Config.user)

apppath='/home/reddit/gamedealsbot/'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=apppath+'msg_monitor.log',
                    filemode='a')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


logging.info("Monitoring inbox...")
while True:
    try:
        for msg in reddit.inbox.stream():
            expired = False
            oops = False
            responded = 0
            # checks if bot has already replied (good if script has to restart)
            try:
                if isinstance(msg, praw.models.Comment):
                    for comment in msg.refresh().replies:
                        try:
                            if comment.author.name == Config.user:
                                responded = 1
                        except AttributeError:
                            responded = 0
                logging.info("Message recieved")
            except AttributeError:
                logging.info("error checking comment by: " + msg.author.name)
            try:
                if responded == 0:
                    if isinstance(msg, praw.models.Comment):
                        text = msg.body.lower()
                        try:
                            if text.index(Config.expired_trigger.lower()) > -1:
                                expired = True
                        except ValueError:
                            pass

                        if oops:
                            msg.mark_read()
                            msg.submission.mod.flair(text=None, css_class=None)
                            logging.info("unflairing... responded to: " + msg.author.name)
                            msg.reply("Flair removed.")
                        elif expired:
                            msg.mark_read()
                            title_url = msg.submission.url
                            #msg.submission.mod.flair(text='Expired', css_class='expired')
                            msg.submission.mod.spoiler()
                            logging.info("flairing... responded to: " + msg.author.name)
                            msg.reply("This deal has been marked expired as requested by "+msg.author.name)
            except AttributeError:
                logging.info("error checking comment by: " + msg.author.name)
    except (prawcore.exceptions.RequestException, prawcore.exceptions.ResponseException):
        logging.info ("Error connecting to reddit servers. Retrying in 5 minutes...")
        time.sleep(300)

    except praw.exceptions.APIException:
        logging.info ("rate limited, wait 5 seconds")
        time.sleep(5)
