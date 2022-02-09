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
import yaml

os.environ['TZ'] = 'UTC'

#from bs4 import BeautifulSoup
reddit = praw.Reddit(client_id=Config.cid,
                     client_secret=Config.secret,
                     password=Config.password,
                     user_agent=Config.agent,
                     username=Config.user)
subreddit = reddit.subreddit(Config.subreddit)

apppath='./'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=apppath+'reddit_response.log',
                    filemode='a')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


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
    con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
    cursorObj = con.cursor()
    cursorObj.execute('DELETE from schedules WHERE postid = "' + submission.id + '"' )
    cursorObj.execute('INSERT into schedules(postid, schedtime) values(?,?)',(submission.id,(submission.created_utc + 2592000)) )
    con.commit()
    con.close()
    post_footer = True
    footer = """

If this deal has expired, you can reply to this comment with `"""+Config.expired_trigger+"""` to automatically close it.  
If this deal has been mistakenly closed or has been restocked, you can open it again by replying with `"""+Config.restore_trigger+"""`.  
[^(more information)](https://www.reddit.com/r/GameDeals/wiki/gamedealsbot)  
^(Note: To prevent abuse, requests are logged publicly.  Intentional abuse will likely result in a ban.)
"""

    wikiconfig = yaml.safe_load( reddit.subreddit('gamedeals').wiki['gamedealsbot-config'].content_md )    

    footer = wikiconfig['footer']
    footer = footer.replace('{{expired trigger}}',wikiconfig['expired-trigger'])
    footer = footer.replace('{{available trigger}}',wikiconfig['available-trigger'])


    reply_reason = "Generic Post"
    reply_text = ""

### Find all URLS inside a .self post
    urls = []
    if not submission.author:
      logging.info("cannot find author?, skipping: " + submission.title)
      return
    if submission.author.name == "gamedealsmod":
      logging.info("gamedealsmod posted, skipping: " + submission.title)
      return
    selfpost = 0
    if submission.is_self:
        selfpost = 1
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


    if "epicgames.com" in url.lower():
      if "free" in submission.title.lower():
        postdate = dateparser.parse( str(submission.created_utc) , settings={'TO_TIMEZONE': 'US/Pacific', 'TIMEZONE': 'UTC' } )

#        if postdate.hour < 8 or postdate.hour > 9: # used for xmas rule, before being permanently disabled via AM to block community posting due to excessive need to moderate
        if postdate.weekday() == 3 and postdate.hour < 8: # removed for EGS's 15 days of games to make the rule more active
          logging.info( "removing early EGS post | https://redd.it/" + submission.id )
          reply = "* We require a deal to be live before posting a submission."
          reply = "* Either this deal has already been submitted,\n\n* Or this deal has been submitted before it is live."
          comment = submission.reply("Unfortunately, your submission has been removed for the following reasons:\n\n" +
          reply +
          "\n\nI am a bot, and this action was performed automatically. Please [contact the moderators of this subreddit](https://www.reddit.com/message/compose/?to=/r/GameDeals) if you have any questions or concerns."
          )
          submission.mod.remove()
          comment.mod.distinguish(sticky=True)
          logID(submission.id)
          return


    if re.search("store.steampowered.com/(sub|app)", url) is not None:
     if submission.author_flair_css_class is not None and submission.is_self:
       return
     r = requests.get( url )

     if re.search("WEEK LONG DEAL", r.text) is not None:
       today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
       monday = today - datetime.timedelta(days=today.weekday())
       datetext = monday.strftime('%Y%m%d')
       con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
       cursorObj = con.cursor()
       cursorObj.execute('SELECT * FROM weeklongdeals WHERE week = ' + datetext )
       rows = cursorObj.fetchall()
       if len(rows) == 0:
         removereason = "* It appears to be a part of the Weeklong deals. \n\nAs there are multiple games on sale, please post a thread with more games in the title [with this link](https://store.steampowered.com/search/?filter=weeklongdeals).\n\nIf you are the developer or publisher of this game, please leave a detailed disclosure as a top level comment as per [Rule 9](https://www.reddit.com/r/GameDeals/wiki/rules#wiki_9._developers_and_publishers), then [contact the mods for approval](https://www.reddit.com/message/compose?to=%2Fr%2FGameDeals)."
       else:
         removereason = "* It appears to be a part of the [Weeklong deals](https://redd.it/" + rows[0][2] + "). \n\nAs there are multiple games on sale, please include a comment within the existing thread to discuss this deal.\n\nIf you are the developer or publisher of this game, please leave a detailed disclosure as a top level comment as per [Rule 9](https://www.reddit.com/r/GameDeals/wiki/rules#wiki_9._developers_and_publishers), then [contact the mods for approval](https://www.reddit.com/message/compose?to=%2Fr%2FGameDeals)."
       comment = submission.reply("Unfortunately, your submission has been removed for the following reasons:\n\n" + 
            removereason +
            "\n\nI am a bot, and this action was performed automatically. Please [contact the moderators of this subreddit](https://www.reddit.com/message/compose/?to=/r/GameDeals) if you have any questions or concerns."
       )
       comment.mod.distinguish(sticky=True)
       submission.mod.remove()
       return


     getexp = getsteamexpiry( url )
     if getexp is not None:
       try:
         con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
         cursorObj = con.cursor()
         cursorObj.execute('DELETE from schedules WHERE postid = "' + submission.id + '"' )
         cursorObj.execute('INSERT into schedules(postid, schedtime) values(?,?)',(submission.id,getexp) )
         con.commit()
         con.close()
         logging.info("[Steam] | " + submission.title + " | https://redd.it/" + submission.id )
         logging.info("setting up schedule: bot for: " + submission.id)
         reply_reason = "Steam Game"
         post_footer = False
         #reply_text = "^(automatic deal expiry set for " + datetime.datetime.fromtimestamp(int(getexp)).strftime('%Y-%m-%d %H:%M:%S') + " UTC)\n\n"
       except:
         pass




    try:
      rules = yaml.safe_load_all( reddit.subreddit('gamedeals').wiki['gamedealsbot-storenotes'].content_md )
    except:
      rules = working_rules
    working_rules = rules

    for rule in rules:
      if rule is not None:
        if "match" in rule:
          if re.search( rule['match'] , url ):
            if "dontmatch" not in rule or not re.search( rule['dontmatch'] , url ):
              #print(rule)
              if "disabled" not in rule or rule['disabled'] == False:
                if "type" not in rule or ( "type" in rule and (rule['type'] == "link" and selfpost == 0) or (rule['type'] == "self" and selfpost == 1) or rule['type'] == "any") :
                  if "reply_reason" in rule:
                    reply_reason = rule['reply_reason']
                  if "reply" in rule:
                    reply_text = rule['reply']
                  if "match-group" in rule:
                    search1 = re.search( rule['match'] , url)
                    match1 = search1.group(rule['match-group'])
                    reply_text.replace('{{match}}', match1)

    if post_footer:
      if reply_text != "":
        comment = submission.reply(reply_text+"\n\n*****\n\n"+footer)
      else:
        comment = submission.reply(footer)
      comment.mod.distinguish(sticky=True)
      logging.info("Replied to: " + submission.title + "   Reason: " + reply_reason)
    logID(submission.id)
    return



#submission = reddit.submission("qiixoa")
#submission = reddit.submission("qijjlf")
#submission = reddit.submission("qijsq0")
#respond( submission )
#exit()



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

                ### handle weeklong deals
                if re.search("steampowered.com.*?filter=weeklongdeals", submission.url) is not None:
                  con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
                  today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  monday = today - datetime.timedelta(days=today.weekday())
                  datetext = monday.strftime('%Y%m%d')
                  cursorObj = con.cursor()
                  cursorObj.execute('SELECT * FROM weeklongdeals WHERE week = ' + datetext )
                  rows = cursorObj.fetchall()
                  if len(rows) == 0:
                    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    monday = today - datetime.timedelta(days=today.weekday())
                    cursorObj.execute('INSERT INTO weeklongdeals (week, post) VALUES (?, ?)', (monday.strftime('%Y%m%d'), submission.id))
                    con.commit()


                ###

### Weekly Post Limit
                if Config.WeeklyPostLimit > 0:
                  currentweek = time.strftime('%Y%W')
                  con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
                  cursorObj = con.cursor()
                  cursorObj.execute('SELECT * FROM weeklyposts WHERE username = "'+submission.author.name+'" AND currentweek = '+currentweek)
                  rows = cursorObj.fetchall()
                  if len(rows) == 0:
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
                  con.close()
###


### Daily Post Limit
                if Config.DailyPostLimit > 0:
                  currentday = time.strftime('%Y%m%d')
                  con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
                  cursorObj = con.cursor()
                  cursorObj.execute('SELECT * FROM dailyposts WHERE username = "'+submission.author.name+'" AND currentday = '+currentday)
                  rows = cursorObj.fetchall()
                  if len(rows) == 0:
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
                  con.close
###




                for top_level_comment in submission.comments:
                    try:
                        if top_level_comment.author and top_level_comment.author.name == Config.user:
                            logID(submission.id)
                            break
                    except AttributeError:
                        pass
                else: # no break before, so no comment from GDB
                    if not donotprocess:
                      respond(submission)
                      continue


    except (prawcore.exceptions.RequestException, prawcore.exceptions.ResponseException):
        logging.info("Error connecting to reddit servers. Retrying in 1 minute...")
        time.sleep(60)

    except praw.exceptions.APIException:
        logging.info("Rate limited, waiting 5 seconds")
        time.sleep(5)
