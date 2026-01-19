import psycopg2

def get_connection():
    return psycopg2.connect(
        dbname="campusdb",
        user="campusadmin",
        password="campus123",
        host="localhost",
        port="5432"
    )
