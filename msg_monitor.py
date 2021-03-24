import sqlite3
import time
import praw
import prawcore 
import requests
import logging
import datetime
import dateparser
import os
import re

os.environ['TZ'] = 'UTC'


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



def checkuser(username):
  commentcount = 0
  commenttime = 0
  currenttime = str(int(time.time()))
  u = reddit.redditor(username)
  try:
    test = u.comment_karma
  except:
    return True
  if int(u.created_utc) > int(time.time()) - (86400 * Config.NewUserDays):
    return True

  if Config.UserKarmaType == "comment":
    karma = reddit.redditor(u.name).comment_karma
  elif Config.UserKarmaType == "link":
    karma = reddit.redditor(u.name).link_karma
  elif Config.UserKarmaType == "combined":
    karma = reddit.redditor(u.name).link_karma + reddit.redditor(u.name).comment_karma
  else:
    karma = 9999999
  if karma <= Config.UserKarma:
    print(Config.UserKarma)
    return True
  for comment in  reddit.redditor(username).comments.new(limit=10) :
    commenttime += ( int(currenttime) - int(comment.created_utc) )
    commentcount += 1
    if comment.subreddit.display_name.lower() in Config.SuspectSubs:
      return True
  #for submission in  reddit.redditor(username).submissions.new(limit=10) :
  #  commenttime += ( int(currenttime) - int(submission.created_utc) )
  #  commentcount += 1
  #  if submission.subreddit.display_name.lower() in Config.SuspectSubs:
  #    return True
  commentdays = ( (commenttime / commentcount) / 86400 )
  #if commentdays >= Config.HistoryDays:
  #  return True
  return False





logging.info("Monitoring inbox...")
while True:
    try:
        for msg in reddit.inbox.stream():
            expired = False
            oops = False
            setsched = False
            responded = 0
            # checks if bot has already replied (good if script has to restart)
            try:
                if isinstance(msg, praw.models.Comment):
                    for comment in msg.refresh().replies:
                        try:
                            if comment.author.name == Config.user:
                                responded = 0
                        except AttributeError:
                            responded = 0
                if msg.author is not None:
                    logging.info("Message recieved from " + msg.author.name + ": " + msg.body)
                    logging.info("* " + msg.submission.id + ": " + msg.submission.title)
            except AttributeError:
                logging.info("error checking comment by: " + msg.author.name)
            try:
                if responded == 0:
                    if isinstance(msg, praw.models.Comment):
                        text = msg.body.lower()
                        u = msg.author
                        ismod = False
                        if msg.author.name in ['dgc1980','SquareWheel','smeggysmeg','smeggysmeg','ronin19','treblah3','caninehere','caninehere','oxygENigma','wayward_wanderer']:
                          ismod = True
                        usertest = checkuser(msg.author.name)
                        try:
                          if text.index(Config.expired_trigger.lower()) > -1:
                            expired = True
                        except ValueError:
                            pass
                        try:
                          if text.index(Config.restore_trigger.lower()) > -1:
                            oops = True
                        except ValueError:
                            pass
                        try:
                          if text.index(Config.expired_schedule.lower()) > -1:
                           if msg.author.name == msg.submission.author.name or ismod and Config.ScheduleType == 'submitter':
                             setsched = True
                           elif ismod and Config.ScheduleType == 'mods':
                             setsched = True
                           elif Config.ScheduleType == 'anyone':
                             setsched = True
                        except ValueError:
                             pass

                        if msg.submission.subreddit != Config.subreddit:
                          setsched = False
                          oops = False
                          expired = False
                          logging.info("abuse https://redd.id/" + msg.submission.id + " by: "+msg.author.name)
                          msg.mark_read()

                        if oops:
                          if not msg.submission.spoiler:
                              myreply = msg.reply("this deal is already available, we use `spoilers` and `flairs` to distinguish a deal has been marked expired").mod.distinguish(how='yes')
                              msg.mark_read()
                              logging.info("already available... responded to: " + msg.author.name)
                          else:
                              msg.submission.mod.unspoiler()
                              msg.submission.mod.flair(text='')
                              logging.info("unflairing " + msg.submission.title + "requested by: "+msg.author.name)
                              con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
                              cursorObj = con.cursor()
                              cursorObj.execute('SELECT * FROM flairs WHERE postid = "'+msg.submission.id+'"')
                              rows = cursorObj.fetchall()
                              msg.mark_read()
                              if len(rows) is not 0 and rows[0][2] != "Expired":
                                try:
                                  cursorObj.execute('DELETE FROM flairs WHERE postid = "'+msg.submission.id+'"')
                                  con.commit()
                                except:
                                  pass
                                msg.submission.mod.flair(text=rows[0][2], css_class='')
                              con.close()
                              msg.reply("This deal has been marked available as requested by /u/"+msg.author.name+".").mod.distinguish(how='yes')
                        elif setsched:
                          #try:
                          if re.search("(\d{1,2}:\d{2} \d{2}\/\d{2}\/\d{4})", text) is not None:
                            con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
                            match1 = re.search("(\d{1,2}:\d{2} \d{2}\/\d{2}\/\d{4})", text)
                            tm = datetime.datetime.strptime(match1.group(1), "%H:%M %d/%m/%Y")
                            tm2 = time.mktime(tm.timetuple())
                            cursorObj = con.cursor()
                            cursorObj.execute('INSERT into schedules(postid, schedtime) values(?,?)',(msg.submission.id,tm2) )
                            con.commit()
                            con.close()
                            logging.info("setting up schedule: " + msg.author.name + "for https://redd.it/" + msg.submission.id + " at " + str(tm.strftime('%Y-%m-%d %H:%M:%S'))  )
                            myreply = msg.reply("This deal has been scheduled to expire as requested by /u/"+msg.author.name+". at " + str(tm.strftime('%Y-%m-%d %H:%M:%S')) + " UTC").mod.distinguish(how='yes')
                            msg.mark_read()
                          else:
                            match1 = re.search("set expiry\ ([\w\:\ \-\+]+)", text)
                            #tm = time.mktime(datetime.datetime.strptime(match1.group(1), "%H:%M %d/%m/%Y").timetuple())
                            print( match1 )
                            tm = dateparser.parse( match1.group(1), settings={'PREFER_DATES_FROM': 'future', 'TIMEZONE': 'UTC', 'TO_TIMEZONE': 'UTC'} )
                            tm2 = time.mktime( tm.timetuple() )
                            con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
                            cursorObj = con.cursor()
                            cursorObj.execute('INSERT into schedules(postid, schedtime) values(?,?)',(msg.submission.id,tm2) )
                            con.commit()
                            con.close()
                            logging.info("setting up schedule: " + msg.author.name + "for https://redd.it/" + msg.submission.id + " at " + str(tm.strftime('%Y-%m-%d %H:%M:%S'))  )
                            myreply = msg.reply("This deal has been scheduled to expire as requested by /u/"+msg.author.name+". at " + str(tm.strftime('%Y-%m-%d %H:%M:%S')) + " UTC").mod.distinguish(how='yes')
                            msg.mark_read()
                          #except:
                          #  pass
                          msg.mark_read()
                        elif expired and not usertest:
                            if msg.submission.spoiler:
                                myreply = msg.reply("This deal has already been marked expired.  We use both spoilers and a unique flair to distinguish deals that are expired.").mod.distinguish(how='yes')
                                msg.mark_read()
                                logging.info("already expired... responded to: " + msg.author.name)
                            else:
                                title_url = msg.submission.url
                                con = sqlite3.connect(apppath+'gamedealsbot.db', timeout=20)
                                cursorObj = con.cursor()
                                if msg.submission.link_flair_text is not None:
                                  if msg.submission.link_flair_text != "Expired":
                                    flairtime = str( int(time.time()))
                                    cursorObj.execute('INSERT INTO flairs(postid, flairtext, timeset) VALUES(?,?,?)', (msg.submission.id,msg.submission.link_flair_text,flairtime ) )
                                    con.commit()
                                msg.submission.mod.spoiler()
                                con.close()
                                msg.submission.mod.flair(text='Expired', css_class='expired')
                                logging.info("flairing... responded to: " + msg.author.name)
                                myreply = msg.reply("This deal has been marked expired as requested by /u/"+msg.author.name+".\n\nIf this was a mistake, please reply with `"+Config.restore_trigger+"`.").mod.distinguish(how='yes')
                                msg.mark_read()
                        elif expired and usertest:
                          msg.report('possible bot abuse')
                          logging.info("maybe abuse from user?: https://reddit.com/u/" + msg.author.name + " on post https://reddit.com/" + msg.submission.id )
                          msg.mark_read()
                        elif oops and usertest:
                          msg.report('possible bot abuse')
                          logging.info("maybe abuse from user?: https://reddit.com/u/" + msg.author.name + " on post https://reddit.com/" + msg.submission.id )
                          msg.mark_read()
                        elif usertest:
                          msg.mark_read()

            except AttributeError:
                raise
                logging.info("error checking comment by: " + msg.author.name)
    except (prawcore.exceptions.RequestException, prawcore.exceptions.ResponseException):
        logging.info ("Error connecting to reddit servers. Retrying in 1 minute...")
        time.sleep(60)

    except praw.exceptions.APIException:
        logging.info ("rate limited, wait 5 seconds")
        time.sleep(5)
