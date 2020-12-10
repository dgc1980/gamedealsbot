import sqlite3

def make_sql_table(con):
    cursorObj = con.cursor()
    cursorObj.execute("CREATE TABLE IF NOT EXISTS dailyposts(id integer PRIMARY KEY, username text, postcount integer, currentday integer)")
    con.commit()
    cursorObj.execute("CREATE TABLE IF NOT EXISTS weeklyposts(id integer PRIMARY KEY, username text, postcount integer, currentweek integer)")
    con.commit()
    cursorObj.execute("CREATE TABLE IF NOT EXISTS flairs(id integer PRIMARY KEY, postid text, flairtext text, timeset integer)")
    con.commit()

    cursorObj.execute("CREATE TABLE IF NOT EXISTS schedules(id integer PRIMARY KEY, postid text, schedtime integer)")
    con.commit()


    cursorObj.execute("CREATE TABLE IF NOT EXISTS awards(id integer PRIMARY KEY, postid text, counted integer)")
    con.commit()

    cursorObj.execute("CREATE TABLE IF NOT EXISTS weeklongdeals(id integer PRIMARY KEY, week text, post text)")
    con.commit()



con = sqlite3.connect('gamedealsbot.db')
make_sql_table(con)

