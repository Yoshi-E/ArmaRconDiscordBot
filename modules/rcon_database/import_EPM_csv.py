#!/usr/bin/python3
import sqlite3 as sl
import csv

# Import an EPM rcon database
# First convert the EPM export (.sdf) to csv:
  # Convert .sdf to .csv with this website https://www.rebasedata.com/convert-sdf-to-csv-online (use at your own risk)
# Extract the zip file and place the "Players.csv" next to the script (in bot/modules/rcon_database/)
# then just import it by running this script (python import_EPM_csv.py)
# Afterwards you can delete the Players.csv and Players.columns files.

# Warning: Importing the same file multiple times will create duplicates.

con = sl.connect('users.db')  
c = con.cursor()

file='Players.csv' #your csv file
with open(file, newline='',encoding='utf8') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
    head = None
    db = []
    for row in spamreader:
        if(head):
            db.append(row[:4])
        else:
            head = row
    sql = 'INSERT INTO users (id, name, beid, ip) values(?, ?, ?, ?)'
    c.executemany(sql, db)
    con.commit()
print("Database Import sucessfull")

