import sqlite3
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

con = sqlite3.connect(apppath+'gamedealsbot.db')

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
                                responded = 0
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
                        try:
                          if text.index(Config.restore_trigger.lower()) > -1:
                             oops = True
                        except ValueError:
                             pass

                        if oops:
                          msg.submission.mod.unspoiler()
                          msg.submission.mod.flair(text='')
                          logging.info("unflairing " + msg.submission.title + "requested by: "+msg.author.name)
                          cursorObj = con.cursor()
                          cursorObj.execute('SELECT * FROM flairs WHERE postid = "'+msg.submission.id+'"')
                          rows = cursorObj.fetchall()
                          if len(rows) is not 0 and rows[0][2] != "Expired":
                            cursorObj.execute('DELETE FROM flairs WHERE postid = "'+msg.submission.id+'"')
                            msg.submission.mod.flair(text=rows[0][2], css_class='')
                          msg.reply("This deal has been marked available as requested by "+msg.author.name+"").mod.distinguish(how='yes')
                          msg.mark_read()
                        elif expired:
                            title_url = msg.submission.url
                            u = msg.author
                            if int(u.created_utc) < int(time.time()) - (86400 * 14):
                              cursorObj = con.cursor()
                              if msg.submission.link_flair_text is not None:
                                if msg.submission.link_flair_text != "Expired":
                                  flairtime = str( int(time.time()))
                                  cursorObj.execute('INSERT INTO flairs(postid, flairtext, timeset) VALUES("'+msg.submission.id+'","'+msg.submission.link_flair_text+'",' + flairtime + ')')
                                  con.commit()
                              msg.submission.mod.spoiler()
                              msg.submission.mod.flair(text='Expired', css_class='expired')
                              logging.info("flairing... responded to: " + msg.author.name)
                              msg.reply("This deal has been marked expired as requested by "+msg.author.name+"  \nif this is a mistake reply with `"+Config.restore_trigger+"`").mod.distinguish(how='yes')
                              msg.report('expiry request')
                            else:
                              msg.report('Request expiration by new user')
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
