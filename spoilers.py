import sqlite3
import time
import praw
import prawcore
import requests
import logging
import Config
import json
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

apppath='/bot/'

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

f = open(apppath+"awards.txt","a+")
f.close()


logging.info("scanning spoiler...")

def runspoiler(postlimit):
 try:
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
    allowsend =0

    if len(submission.all_awardings) > 0 :
      #print("has awards")
      if submission.id in open(apppath+'awards.txt').read():
        continue

      con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
      cursorObj = con.cursor()
      cursorObj.execute('SELECT * FROM awards WHERE postid = "'+submission.id+'"')
      rows = cursorObj.fetchall()
      if len(rows) is not 0:
        # already has awards
        if rows[0][2] < len(submission.all_awardings):
          logging.info("found more awards on :" + submission.id)
          cursorObj.execute('UPDATE awards SET counted = ? WHERE postid = ?', (len(submission.all_awardings),submission.id)  )
          con.commit()
          con.close()
          has_gild = ""
          for award in submission.all_awardings:
            print( "Award......: " + award['name'] )
            if award['name'] == "Silver":
              has_gild = "** Silver/Gold/Plat found **"
            if award['name'] == "Gold":
              has_gild = "** Silver/Gold/Plat found **"
            if award['name'] == "Platinum":
              has_gild = "** Silver/Gold/Plat found **"

            if award['name'] != "Silver" and award['name'] != "Gold" and award['name'] != "Platinum" and award['name'] != "[deleted]":
              allowsend = 1

          if allowsend == 1:
            reddit.subreddit('gamedeals').message('Post Awards Again', 'There has been an Award found on https://new.reddit.com/r/GameDeals/comments/' + submission.id)
            #reddit.subreddit('gamedeals').message('Post Awards Again', 'There has been an Award found on https://new.reddit.com/r/GameDeals/comments/' + submission.id + '\n\n' + has_gild)


      else:
        #first time
        logging.info("found awards on :" + submission.id)
        cursorObj.execute('INSERT INTO awards(postid, counted) VALUES(?, ?)', (submission.id, 1)  )
        con.commit()
        con.close()
        has_gild = ""
        for award in submission.all_awardings:
          if award['name'] == "Silver":
            has_gild = "** Silver/Gold/Plat found **"
          if award['name'] == "Gold":
            has_gild = "** Silver/Gold/Plat found **"
          if award['name'] == "Platinum":
            has_gild = "** Silver/Gold/Plat found **"
          if award['name'] != "Silver" and award['name'] != "Gold" and award['name'] != "Platinum" and award['name'] != "[deleted]":
            allowsend = 1

        if allowsend == 1:
          #reddit.subreddit('gamedeals').message('Post Awards', 'There has been an Award found on https://new.reddit.com/r/GameDeals/comments/' + submission.id + '\n\n' + has_gild)
          reddit.subreddit('gamedeals').message('Post Awards', 'There has been an Award found on https://new.reddit.com/r/GameDeals/comments/' + submission.id)


    if submission.spoiler and not isflair :
      if not isflair and flair != "":
        flairtime = str( int(time.time()))
        con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
        cursorObj = con.cursor()
        cursorObj.execute('INSERT INTO flairs(postid, flairtext, timeset) VALUES(?,?,?)', (submission.id,submission.link_flair_text,flairtime)  )
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
 except (prawcore.exceptions.RequestException, prawcore.exceptions.ResponseException):
        logging.info("Error connecting to reddit servers. Retrying in 1 minute...")
        time.sleep(60)

 except praw.exceptions.APIException:
        logging.info("Rate limited, waiting 5 seconds")
        time.sleep(5)
 


schedule.every(1).minutes.do(runspoiler, 50)
schedule.every(1).hours.do(runspoiler, 200)

runspoiler(10)

while 1:
#  try:
    schedule.run_pending()
    time.sleep(1)

#  except:
#    time.sleep(10)
