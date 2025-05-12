from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging # Added for logging

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Updated CORS configuration for better explicitness
CORS(app, origins="http://localhost:5173", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization"], supports_credentials=True)

# Configure logging
logging.basicConfig(level=logging.INFO) # For general Flask/werkzeug logs
app.logger.setLevel(logging.DEBUG) # Set app's own logger to DEBUG to see more details

# Database configuration
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'expense_management')
# MYSQL_CURSORCLASS is usually set when you create the cursor, not in app.config for mysql.connector
# However, if you were using Flask-MySQLdb, it would be relevant.
# For mysql.connector, you typically get a dictionary cursor by cursor = db.cursor(dictionary=True)

# Initialize DB with the app
import db
db.init_app(app)

# Import and register blueprints
from routes.invoice_routes import invoice_bp
app.register_blueprint(invoice_bp)
# You would register other blueprints (e.g., for users) here as well

@app.route('/')
def home():
    return jsonify({'message': 'Welcome to the Expense Management API!'})

# Example route (can be removed later)
@app.route('/api/test')
def test_route():
    # Test database connection
    conn = db.get_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 'Database connection successful!' AS message;")
            result = cursor.fetchone()
            cursor.close()
            return jsonify({'status': 'success', 'message': 'API is working!', 'db_message': result[0] if result else "Could not fetch DB message"})
        except Exception as e:
            app.logger.error(f"DB test error: {e}")
            return jsonify({'status': 'success', 'message': 'API is working but DB test failed.', 'db_error': str(e)}), 500
    else:
        return jsonify({'status': 'error', 'message': 'API is working but could not connect to the database.'}), 500

# Route to initialize DB schema (for development/setup)
@app.route('/api/init-db', methods=['POST'])
def init_db_route():
    # Add some security here in a real app (e.g., check for a secret key or admin user)
    # For now, it's open for easy setup.
    app.logger.info("Attempting to initialize database schema...")
    try:
        with app.app_context(): # Ensure we are within an app context
            db.init_db_schema()
        return jsonify({'message': 'Database schema initialization attempted. Check logs for details.'}), 200
    except Exception as e:
        app.logger.error(f"Error during init-db route: {e}")
        return jsonify({'message': f'Error initializing database schema: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Set debug=False for production if FLASK_ENV is 'production'
    is_debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=is_debug, host='0.0.0.0', port=port) 