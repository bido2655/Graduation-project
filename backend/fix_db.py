from sqlalchemy import text
from app.database import engine, Base
from app.models import db_models

def fix_schema():
    print("Connecting to database...")
    with engine.connect() as connection:
        # Check if pin column exists in password_resets
        print("Checking 'password_resets' table structure...")
        try:
            # Try to add the pin column
            connection.execute(text("ALTER TABLE password_resets DROP COLUMN IF EXISTS token"))
            connection.execute(text("ALTER TABLE password_resets ADD COLUMN pin VARCHAR(10) NOT NULL AFTER user_id"))
            connection.execute(text("ALTER TABLE password_resets ADD INDEX (pin)"))
            connection.commit()
            print("Successfully added 'pin' column to 'password_resets' table.")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("'pin' column already exists.")
            else:
                print(f"Error updating table: {e}")
                print("Attempting to drop and recreate the table instead...")
                try:
                    connection.execute(text("DROP TABLE IF EXISTS password_resets"))
                    connection.commit()
                    Base.metadata.create_all(bind=engine)
                    print("Successfully recreated 'password_resets' table.")
                except Exception as e2:
                    print(f"Failed to fix table: {e2}")

if __name__ == "__main__":
    fix_schema()
