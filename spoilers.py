import sqlite3
import time
import praw
import prawcore
import requests
import logging
import Config
from bs4 import BeautifulSoup
import schedule
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

logging.getLogger('schedule').propagate = False


logging.info("scanning spoiler...")

def runspoiler(postlimit):
  for submission in subreddit.new(limit=postlimit):
    if submission.link_flair_text is not None:
      flair = submission.link_flair_text.lower()
    else:
      flair = ""
    isflair = False
    try:
      if flair.index('expired') > -1:
        isflair = True
    except ValueError:
      pass

    if submission.spoiler and not isflair :
      if not isflair and flair != "":
        flairtime = str( int(time.time()))
        con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
        cursorObj = con.cursor()
        cursorObj.execute('INSERT INTO flairs(postid, flairtext, timeset) VALUES(?,?,?)', (submission.id,submission.link_flair_text,flairtime)  )
        #cursorObj.execute('INSERT INTO flairs(postid, flairtext, timeset) VALUES("'+submission.id+'","'+submission.link_flair_text+'",' + flairtime + ')')
        con.commit()
        con.close()
      #if submission.mod.flair != "":
      #  submission.mod.flair(text='Expired: ' + submission.mod.flair, css_class='expired')
      #else
      #  submission.mod.flair(text='Expired', css_class='expired')
      submission.mod.flair(text='Expired', css_class='expired')

      logging.info("flairing spoiled post of " + submission.title)
    elif not submission.spoiler and isflair:
      submission.mod.flair(text='')
      logging.info("unflairing spoiled post of " + submission.title)
      con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
      cursorObj = con.cursor()
      cursorObj.execute('SELECT * FROM flairs WHERE postid = "'+submission.id+'"')
      rows = cursorObj.fetchall()
      if len(rows) is not 0 and rows[0][2] != "Expired":
        cursorObj.execute('DELETE FROM flairs WHERE postid = "'+submission.id+'"')
        submission.mod.flair(text=rows[0][2], css_class='')
      con.close()



schedule.every(1).minutes.do(runspoiler, 50)
schedule.every(1).hours.do(runspoiler, 200)

runspoiler(200)

while 1:
    schedule.run_pending()
    time.sleep(1)

