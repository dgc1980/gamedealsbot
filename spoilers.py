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
subreddit = reddit.subreddit(Config.subreddit)

apppath='/home/reddit/gamedealsbot/'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=apppath+'spoiler_monitor.log',
                    filemode='a')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


logging.info("scanning spoiler...")

while True:
  for submission in subreddit.new(limit=50):
    if submission.spoiler and submission.link_flair_text != "Expired":
      submission.mod.flair(text='Expired', css_class='expired')
      logging.info("flairing spoiled post of " + submission.title);
  time.sleep(30)
