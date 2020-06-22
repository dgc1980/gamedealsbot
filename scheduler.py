import sqlite3
import time
import praw
import prawcore
import logging
import datetime
import os
import re
import schedule

import Config

os.environ['TZ'] = 'UTC'


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
                    filename=apppath+'scheduler.log',
                    filemode='a')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
logging.getLogger('schedule').propagate = False



con = sqlite3.connect(apppath+'gamedealsbot.db')

logging.info("starting scheduler...")


def runjob():
  tm = str(int(time.time()))
  cursorObj = con.cursor()
  cursorObj.execute('SELECT * FROM schedules WHERE schedtime <= ' + tm + ';')
  rows = cursorObj.fetchall()
  if len(rows) is not 0:
    for row in rows:
      if reddit.submission(row[1]).removed_by_category is not "None":
        logging.info("running schedule on https://reddit.com/" + row[1])
        cursorObj.execute('DELETE FROM schedules WHERE postid = "'+ row[1]+'"')
        con.commit()
        reddit.submission(row[1]).mod.spoiler()





schedule.every(1).minutes.do(runjob)

runjob()
while 1:
    schedule.run_pending()
    time.sleep(1)

