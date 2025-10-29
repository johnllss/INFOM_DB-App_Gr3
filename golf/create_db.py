import mysql.connector

mydb = mysql.connector.connect(
    host = "localhost",
    user = "root",
    password = "password123",
    database= "dbgolf"
)
print("Connected", mydb)