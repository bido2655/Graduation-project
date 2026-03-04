import sys
import os
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL, DB_NAME

def check_connection():
    print(f"Testing connection to: {DATABASE_URL.replace(':' + DATABASE_URL.split(':')[2].split('@')[0], ':****')}")
    
    encoded_url = DATABASE_URL
    # Handle empty password case for pymysql which might need explicit handling or just works
    
    try:
        engine = create_engine(encoded_url)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Successfully connected to MySQL server!")
            
            # Check if database exists
            result = connection.execute(text(f"SHOW DATABASES LIKE '{DB_NAME}'"))
            if result.fetchone():
                print(f"Database '{DB_NAME}' exists.")
            else:
                print(f"Database '{DB_NAME}' does NOT exist.")
                print("You may need to create it manually in phpMyAdmin or I can try to create it.")
                
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_connection()
