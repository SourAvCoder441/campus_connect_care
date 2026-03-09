import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root (go up 3 levels from student_limit/app/db/)
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

def get_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'campusdb'),
            user=os.getenv('DB_USER', 'campusadmin'),
            password=os.getenv('DB_PASSWORD', 'campus123'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise
