import sqlite3

def make_sql_table(con):
    cursorObj = con.cursor()
    cursorObj.execute("CREATE TABLE dailyposts(id integer PRIMARY KEY, username text, postcount integer, currentday integer)")
    con.commit()
    cursorObj.execute("CREATE TABLE weeklyposts(id integer PRIMARY KEY, username text, postcount integer, currentweek integer)")
    con.commit()

con = sqlite3.connect('gamedealsbot.db')
make_sql_table(con)

