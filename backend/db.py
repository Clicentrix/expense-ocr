import mysql.connector
from mysql.connector import Error
from flask import current_app, g
import os

def get_db():
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(
                host=current_app.config['MYSQL_HOST'],
                user=current_app.config['MYSQL_USER'],
                password=current_app.config['MYSQL_PASSWORD'],
                database=current_app.config['MYSQL_DB']
            )
            current_app.logger.info(f"Successfully connected to MySQL database: {current_app.config['MYSQL_DB']}")
        except Error as e:
            current_app.logger.error(f"Error connecting to MySQL Database: {e}")
            g.db = None # Ensure db is None if connection fails
            # Optionally, re-raise the error or handle it as needed
            # raise e 
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
        current_app.logger.info("MySQL connection closed.")

def init_app(app):
    app.teardown_appcontext(close_db)
    # We might add a CLI command here later to initialize the DB schema
    # app.cli.add_command(init_db_command)

def init_db_schema():
    """Initializes the database schema based on schema.sql."""
    db = get_db()
    if not db:
        current_app.logger.error("Cannot initialize schema, DB connection failed.")
        return

    cursor = db.cursor()
    # Path to your schema file
    schema_file_path = os.path.join(os.path.dirname(__file__), 'schema.sql') 
    try:
        with open(schema_file_path, 'r') as f:
            # Split statements by semicolon and filter out empty ones
            sql_statements = [s.strip() for s in f.read().split(';') if s.strip()]
            for statement in sql_statements:
                if statement: # Ensure statement is not empty
                    cursor.execute(statement)
        db.commit()
        current_app.logger.info("Database schema initialized.")
    except Error as e:
        current_app.logger.error(f"Error initializing schema: {e}")
        db.rollback()
    except FileNotFoundError:
        current_app.logger.error(f"Schema file not found at {schema_file_path}")
    finally:
        cursor.close() 