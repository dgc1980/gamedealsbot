import sqlite3

def make_sql_table(con):
    cursorObj = con.cursor()
    cursorObj.execute("CREATE TABLE IF NOT EXISTS dailyposts(id integer PRIMARY KEY, username text, postcount integer, currentday integer)")
    con.commit()
    cursorObj.execute("CREATE TABLE IF NOT EXISTS weeklyposts(id integer PRIMARY KEY, username text, postcount integer, currentweek integer)")
    con.commit()
    cursorObj.execute("CREATE TABLE IF NOT EXISTS flairs(id integer PRIMARY KEY, postid text, flairtext text, timeset integer)")
    con.commit()

con = sqlite3.connect('gamedealsbot.db')
make_sql_table(con)

