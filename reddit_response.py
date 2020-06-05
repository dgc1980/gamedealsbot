#!/usr/bin/python3

import sqlite3
import time
import praw
import prawcore
import requests
import os
import datetime
import Config
import logging
import re
import dateparser


from bs4 import BeautifulSoup
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
                    filename=apppath+'reddit_response.log',
                    filemode='a')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)

class Error(Exception):
    """Base class"""
    pass

class LinkError(Error):
    """Could not parse the URL"""
    pass

# make an empty file for first run
f = open(apppath+"postids.txt","a+")
f.close()


def getsteamexpiry(steamurl):
  headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36'}
  cookies = {
                'wants_mature_content': '1',
                'birthtime': '-2148631199',
                'lastagecheckage': '1-0-1902' }
  r = requests.get(steamurl, headers=headers, cookies=cookies )
  # Offer ends 13 June</p>
  if re.search("\$DiscountCountdown", r.text) is not None:
    match1 = re.search("\$DiscountCountdown, ([\d]+)", r.text)
    return match1.group(1)
  elif re.search("Offer ends ([\w\ ]+)</p>", r.text) is not None:
    match1 = re.search("Offer ends ([\w\ ]+)</p>", r.text)
    enddate= dateparser.parse( "10am " + match1.group(1)  , settings={'PREFER_DATES_FROM': 'future', 'TIMEZONE': 'US/Pacific','TO_TIMEZONE': 'UTC' } )
    return time.mktime( enddate.timetuple() )
  return



def logID(postid):
    f = open(apppath+"postids.txt","a+")
    f.write(postid + "\n")
    f.close()


def respond(submission):
    post_footer = True
    footer = """

If this deal has expired, you can reply to this comment with `"""+Config.expired_trigger+"""` to automatically close it.  
If this deal has been mistakenly closed or has been restocked, you can open it again by replying with `"""+Config.restore_trigger+"""`.  
[^(more information)](https://www.reddit.com/r/GameDeals/wiki/gamedealsbot)  
^(Note: To prevent abuse, requests are logged publicly.  Intentional abuse will likely result in a ban.)
"""

    reply_reason = "Generic Post"
    reply_text = ""

### Find all URLS inside a .self post
    urls = []
    if submission.is_self:
        urls = re.findall('(?:(?:https?):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+', submission.selftext)
        if len(urls) == 0:
            logging.info("NO LINK FOUND skipping: " + submission.title)
            logID(submission.id)
            return
    # remove duplicate URLs
        unique_urls = []
        for url in urls:
          if url in unique_urls:
            continue
          else:
            unique_urls.append(url)

        url = urls[0]    ### use only the first url
### get url for link post
    if not submission.is_self:
      url = submission.url

    if re.search("store.steampowered.com/(sub|app)", url) is not None:
     getexp = getsteamexpiry( url )
     if getexp is not None:
       try:
         cursorObj = con.cursor()
         cursorObj.execute('INSERT into schedules(postid, schedtime) values(?,?)',(submission.id,getexp) )
         con.commit()
         logging.info("setting up schedule: bot for: " + submission.id)
         reply_reason = "Steam Game"
         post_footer = False
         #reply_text = "^(automatic deal expiry set for " + datetime.datetime.fromtimestamp(int(getexp)).strftime('%Y-%m-%d %H:%M:%S') + " UTC)\n\n"
       except:
         pass

### Bundle Giveaways
    if re.search("(humblebundle\.com(?!(/store|/monthly))|fanatical\.com/(.*)bundle|(?!freebies\.)indiegala\.com(?!(/store|/crackerjack)))", url) is not None:
      if re.search("indiegala.com.+giveaway", url) is None and re.search("freebies.indiegala.com", url) is None:
        reply_reason = "Bundle Giveaway"
        reply_text = """
**Giveaways**

If you wish to give away your extra game keys, please post them under this comment only.  Do not ask for handouts or trades."""

### chrono.gg auto expire
    if re.search("chrono.gg", url) is not None:
      try:
        r = requests.get( url )
        match1 = re.search('"endsAt":"([\w\-\:\.]+)"', r.text)
        enddate= dateparser.parse( match1.group(1)  , settings={'PREFER_DATES_FROM': 'future', 'TO_TIMEZONE': 'UTC' } )
        expdate = time.mktime( enddate.timetuple() )
        cursorObj = con.cursor()
        cursorObj.execute('INSERT into schedules(postid, schedtime) values(?,?)',(submission.id,expdate) )
        con.commit()
        logging.info("setting up schedule: bot for: " + submission.id)
        reply_reason = "chrono.gg"
        post_footer = False
        #reply_text = "^(automatic deal expiry set for " + datetime.datetime.fromtimestamp(int(expdate)).strftime('%Y-%m-%d %H:%M:%S') + " UTC)\n\n"
      except:
        pass

### GOG.com Info
    if re.search("gog.com", url) is not None:
      reply_reason = "GOG.com Info"
      reply_text = """
GOG.com sells games that are completely DRM-free. This means that there is nothing preventing or limiting you from installing and playing the game. 

**As such, games from GOG never come with Steam keys.**

[More Information](https://support.gog.com/hc/en-us/articles/360001947574-FAQ-What-is-GOG-COM-?product=gog)

This message is posted automatically to inform new users about what this service provides in order to answer some commonly asked questions."""

### Itch.io
#    if re.search("itch.io", url) is not None:
#      reply_reason = "Itch.io Info"
#      reply_text = """
#Games from EA Origin do not come with Steam keys, unless explicitly stated. Origin games will require the download and use of the Origin client. If you wish to add a game shortcut to your Steam library, you can do so by adding it as a *Non-Steam Game* from the *Games* menu of the Steam client.
#
#[More Information](http://www.origin.com/us/faq)"""
#
### Origin
    if re.search("origin.com", url) is not None:
      reply_reason = "Origin Info"
      reply_text = """
Games from EA Origin do not come with Steam keys, unless explicitly stated. Origin games will require the download and use of the Origin client. If you wish to add a game shortcut to your Steam library, you can do so by adding it as a *Non-Steam Game* from the *Games* menu of the Steam client.

[More Information](http://www.origin.com/us/faq)"""

### Groupees Preorders

    if re.search("groupees.com", url) is not None:
      if re.search("(pre-?order|pre-?purchase|preorder|pre order|presale|pre sale|pre-sale)", submission.title.lower() ) is not None:
        reply_reason = "Groupees Preorder"
        reply_text = """
About Groupees' pre-orders:  

This is a blind pre-purchase of the full bundle at a reduced price. The games will be revealed tomorrow at normal price"""


### IndieGala Giveaway Explanation
    if re.search("indiegala\.com.+giveaway", url) is not None:
      reply_reason = "IndieGala giveaways"
      reply_text = "IndieGala giveaways are usually located towards the bottom of the page.  You may need to dismiss a banner image or confirm a captcha to claim a key.\n"

### IndieGala freebies Explanation
    if re.search("freebies\.indiegala\.com", url) is not None:
      reply_reason = "IndieGala freebies"
      reply_text = "IndieGala freebies are usually DRM-free downloads.  In these cases no Steam key will be provided."

### Fireflower Games
    if re.search("fireflowergames\.com", url) is not None:
      reply_reason = "Fireflower Games"
      reply_text = """
FireFlower Games sells games that are completely DRM-free. This means that there is nothing preventing or limiting you from installing and playing the game.

**As such, games from FireFlower Games never come with Steam keys.**

[More Information](https://fireflowergames.com/faq)

This message is posted automatically to answer some commonly asked questions about what this service provides"""

### Amazon US Charities
    if re.search("(amazon\.com\/(.*\/)?dp|amazon\.com\/(.*\/)?gp\/product|amazon\.com\/(.*\/)?exec\/obidos\/ASIN|amzn\.com)\/(\w{10})", url) is not None:
      match1 = re.search("(amazon\.com\/(.*\/)?dp|amazon\.com\/(.*\/)?gp\/product|amazon\.com\/(.*\/)?exec\/obidos\/ASIN|amzn\.com)\/(\w{10})", url)
      amzn = match1.group(5)
      reply_reason = "Amazon US Charities"
      reply_text = """
Charity links:

* [Child's Play](https://smile.amazon.com/dp/"""+amzn+"""?tag=childsplaycha-20)
* [Electronic Frontier Foundation](https://smile.amazon.com/dp/"""+amzn+"""?tag=electronicfro-20)
* [Able Gamers](https://smile.amazon.com/dp/"""+amzn+"""?tag=ablegamers-20)
* [Mercy Corps](https://smile.amazon.com/dp/"""+amzn+"""?tag=mercycorps-20)"""

### Amazon US Charities NODE
    if re.search("amazon\.com\/.*node=(\d+)", url) is not None:
      match1 = re.search("(amazon\.com\/(.*\/)?dp|amazon\.com\/(.*\/)?gp\/product|amazon\.com\/(.*\/)?exec\/obidos\/ASIN|amzn\.com)\/(\w{10})", url)
      amzn = match1.group(1)
      reply_reason = "Amazon US Charities"
      reply_text = """
Charity links:

* [Child's Play](https://smile.amazon.com/b/?node="""+amzn+"""&tag=childsplaycha-20)
* [Electronic Frontier Foundation](https://smile.amazon.com/b/?node="""+amzn+"""&tag=electronicfro-20)
* [Able Gamers](https://smile.amazon.com/b/?node="""+amzn+"""&tag=ablegamers-20)
* [Mercy Corps](https://smile.amazon.com/b/?node="""+amzn+"""&tag=mercycorps-20)"""


### Amazon UK Charities
    if re.search("(amazon\.co\.uk\/(.*\/)?dp|amazon\.co\.uk\/(.*\/)?gp\/product|amazon\.co\.uk\/(.*\/)?exec\/obidos\/ASIN|amzn\.co\.uk)\/(\w{10})", url) is not None:
      match1 = re.search("(amazon\.co\.uk\/(.*\/)?dp|amazon\.co\.uk\/(.*\/)?gp\/product|amazon\.co\.uk\/(.*\/)?exec\/obidos\/ASIN|amzn\.co\.uk)\/(\w{10})", url)
      amzn = match1.group(5)
      reply_reason = "Amazon UK Charities"
      reply_text = """
Charity links:

* [Centre Point](https://www.amazon.co.uk/dp/"""+amzn+"""?tag=centrepoint01-21)"""

### Amazon UK Charities NODE
    if re.search("amazon\.co\.uk\/.*node=(\d+)", url) is not None:
      match1 = re.search("amazon\.co\.uk\/.*node=(\d+)", url)
      amzn = match1.group(1)
      reply_reason = "Amazon UK Charities"
      reply_text = """
Charity links:

* [Centre Point](https://www.amazon.co.uk/dp/?node="""+amzn+"""&tag=centrepoint01-21)"""



    if post_footer:
      if reply_text is not "":
        comment = submission.reply(reply_text+"\n\n*****\n\n"+footer)
      else:
        comment = submission.reply(footer)
      comment.mod.distinguish(sticky=True)
      logging.info("Replied to: " + submission.title + "   Reason: " + reply_reason)
    logID(submission.id)
    return

while True:
    try:
        logging.info("Initializing bot...")
        for submission in subreddit.stream.submissions():
            if submission.created < int(time.time()) - 86400:
                continue
            if submission.title[0:1].lower() == "[" or submission.title[0:1].lower() == "[":


                if submission.id in open(apppath+'postids.txt').read():
                    continue
                #logging.info("Week: "+time.strftime('%Y%W'))
                #logging.info("Day: "+time.strftime('%Y%m%d'))
                #logging.info("User: "+submission.author.name)

                donotprocess=False
### Weekly Post Limit
                if Config.WeeklyPostLimit > 0:
                  currentweek = time.strftime('%Y%W')
                  cursorObj = con.cursor()
                  cursorObj.execute('SELECT * FROM weeklyposts WHERE username = "'+submission.author.name+'" AND currentweek = '+currentweek)
                  rows = cursorObj.fetchall()
                  if len(rows) is 0:
                    cursorObj.execute('INSERT INTO weeklyposts(username, postcount, currentweek) VALUES("'+submission.author.name+'",1,'+currentweek+')')
                    con.commit()
                  else:
                    curcount = rows[0][2]
                    if int(curcount) > int(Config.WeeklyPostLimit):
                      donotprocess=True
                      logging.info(submission.author.name+' is over their weekly post limit')
                      submission.mod.remove()
                      comment = submission.reply("Thank you for your submission, but you have reached your weekly post limit\n\n^^^^^\n\nYou may contact the modderators if you feel you are being picked on")
                      comment.mod.distinguish(sticky=True)
                    else:
                      curcount=curcount+1
                      cursorObj.execute("UPDATE weeklyposts SET postcount = " + str(curcount) + ' WHERE id = ' + str(rows[0][0]))
                      con.commit()
###


### Daily Post Limit
                if Config.DailyPostLimit > 0:
                  currentday = time.strftime('%Y%m%d')
                  cursorObj = con.cursor()
                  cursorObj.execute('SELECT * FROM dailyposts WHERE username = "'+submission.author.name+'" AND currentday = '+currentday)
                  rows = cursorObj.fetchall()
                  if len(rows) is 0:
                    cursorObj.execute('INSERT INTO dailyposts(username, postcount, currentday) VALUES("'+submission.author.name+'",1,'+currentday+')')
                    con.commit()
                  else:
                    curcount = rows[0][2]
                    if int(curcount) > int(Config.DailyPostLimit):
                      donotprocess=True
                      logging.info(submission.author.name+' is over their daily post limit')
                      submission.mod.remove()
                      comment = submission.reply("Thank you for your submission, but you have reached your daily post limit\n\n^^^^^\n\nYou may contact the modderators if you feel you are being picked on")
                      comment.mod.distinguish(sticky=True)
                    else:
                      curcount=curcount+1
                      cursorObj.execute("UPDATE dailyposts SET postcount = " + str(curcount) + ' WHERE id = ' + str(rows[0][0]))
                      con.commit()
###




                for top_level_comment in submission.comments:
                    try:
                        if top_level_comment.author and top_level_comment.author.name == Config.user:
                            logID(submission.id)
                            break
                    except AttributeError:
                        pass
                else: # no break before, so no comment from GPDBot
                    if not donotprocess:
                      respond(submission)
                      continue


    except (prawcore.exceptions.RequestException, prawcore.exceptions.ResponseException):
        logging.info("Error connecting to reddit servers. Retrying in 1 minute...")
        time.sleep(60)

    except praw.exceptions.APIException:
        logging.info("Rate limited, waiting 5 seconds")
        time.sleep(5)
