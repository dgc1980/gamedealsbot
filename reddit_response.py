import time
import praw
import prawcore
import requests
import Config
import logging
import re
from bs4 import BeautifulSoup
reddit = praw.Reddit(client_id=Config.cid,
                     client_secret=Config.secret,
                     password=Config.password,
                     user_agent=Config.agent,
                     username=Config.user)
subreddit = reddit.subreddit(Config.subreddit)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='reddit_response.log',
                    filemode='w')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


class Error(Exception):
    """Base class"""
    pass

class LinkError(Error):
    """Could not parse the URL"""
    pass

# make an empty file for first run
f = open("postids.txt","a+")
f.close()

def logID(postid):
    f = open("postids.txt","a+")
    f.write(postid + "\n")
    f.close()

def respond(submission):
    footer = """

If this deal has expired, you can reply to this comment with `"""+Config.expired_trigger+"""` to have it marked as such.

*****

^^^any ^^^abuse ^^^of ^^^this ^^^will ^^^result ^^^in ^^^being ^^^banned  
^^^I ^^^am ^^^a ^^^bot, ^^^if ^^^you ^^^have ^^^any ^^^questions ^^^or ^^^comments ^^^about ^^^this ^^^post, ^^^please [^^^message ^^^the ^^^moderators](https://www.reddit.com/message/compose?to=%2Fr%2FGameDeals)"""

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


### Bundle Giveaways
    if re.search("(humblebundle\.com(?!(/store|/monthly))|fanatical\.com/(.*)bundle|(?!freebies\.)indiegala\.com(?!(/store|/crackerjack)))", url) is not None:
      if re.search("indiegala.com.+giveaway", url) is None and re.search("freebies.indiegala.com", url) is None:
        reply_reason = "Bundle Giveaway"
        reply_text = """
**Giveaways**

If you wish to give away your extra game keys, please post them under this comment only.  Do not ask for handouts or trades."""


### GOG.com Info
    if re.search("gog.com", url) is not None:
      reply_reason = "GOG.com Info"
      reply_text = """
GOG.com sells games that are completely DRM-free. This means that there is nothing preventing or limiting you from installing and playing the game. 

**As such, games from GOG never come with Steam keys.**

[More Information](https://support.gog.com/hc/en-us/articles/360001947574-FAQ-What-is-GOG-COM-?product=gog)

This message is posted automatically to inform new users about what this service provides in order to answer some commonly asked questions."""

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
    if re.search("freebies.indiegala.com", url) is not None:
      reply_reason = "IndieGala freebies"
      reply_text = "IndieGala freebies are usually DRM-free downloads.  In these cases no Steam key will be provided."

### Fireflower Games
    if re.search("freebies.indiegala.com", url) is not None:
      reply_reason = "Fireflower Games"
      reply_text = """
FireFlower Games sells games that are completely DRM-free. This means that there is nothing preventing or limiting you from installing and playing the game.

**As such, games from FireFlower Games never come with Steam keys.**

[More Information](http://www.fireflowergames.com/faq/)

This message is posted automatically to answer some commonly asked questions about what this service provides"""

### Amazon US Charities
    if re.search("(amazon\.com\/(.*\/)?dp|amazon\.com\/(.*\/)?gp\/product|amazon\.com\/(.*\/)?exec\/obidos\/ASIN|amzn\.com)\/(\w{10})", url) is not None or re.search("amazon\.com\/.*node=(\d+)", url) is not None:
      reply_reason = "Amazon US Charities"
      reply_text = """
Charity links:

* [Child's Play](http://smile.amazon.com/b?node={{match-url-2}}&tag=childsplaycha-20)
* [Electronic Frontier Foundation](http://smile.amazon.com/b?node={{match-url-2}}&tag=electronicfro-20)
* [Able Gamers](http://smile.amazon.com/b?node={{match-url-2}}&tag=ablegamers-20)
* [Mercy Corps](http://smile.amazon.com/b?node={{match-url-2}}&tag=mercycorps-20)"""

### Amazon UK Charities
    if re.search("(amazon\.co\.uk\/(.*\/)?dp|amazon\.co\.uk\/(.*\/)?gp\/product|amazon\.co\.uk\/(.*\/)?exec\/obidos\/ASIN|amzn\.co\.uk)\/(\w{10})", url) is not None or re.search("amazon\.co\.uk\/.*node=(\d+)", url) is not None:
      reply_reason = "Amazon UK Charities"
      reply_text = """
Charity links:

* [Centre Point](http://www.amazon.co.uk/b?node={{match-url-2}}&tag=centrepoint01-21)"""



    if reply_text is not "":
      comment = submission.reply(reply_text+"\n*****\n"+footer)
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
                if submission.id in open('postids.txt').read():
                    continue
                for top_level_comment in submission.comments:
                    try:
                        if top_level_comment.author and top_level_comment.author.name == Config.user:
                            logID(submission.id)
                            break
                    except AttributeError:
                        pass
                else: # no break before, so no comment from GPDBot
                    respond(submission)
                    continue
    except (prawcore.exceptions.RequestException, prawcore.exceptions.ResponseException):
        logging.info("Error connecting to reddit servers. Retrying in 5 minutes...")
        time.sleep(300)

    except praw.exceptions.APIException:
        logging.info("Rate limited, waiting 5 seconds")
        time.sleep(5)
