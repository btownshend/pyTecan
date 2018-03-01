import sqlite3
from Tkinter import *

import sqlite3

parent = Tk()


def makeentry(parent, caption, value,width=None, **options):
    Label(parent, text=caption).pack(side=LEFT)
    entry = Entry(parent, **options)
    if width:
        entry.config(width=width)
    entry.pack(side=LEFT)
    entry.insert(0,value)
    return entry


db=sqlite3.connect('test.db')
cursor=db.cursor()
cursor.execute("select flag,value  from  flags order by flag")
for res in cursor:
    makeentry(parent, res[0], res[1])

mainloop()
 
