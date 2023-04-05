
import pyodbc

def get_table_names():
    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=server_name;DATABASE=database_name;Trusted_Connection=yes;')
    cursor = conn.cursor()
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA='dbo';")
    table_names = [table[0