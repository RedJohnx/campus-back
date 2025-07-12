import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient
import firebase_admin
from firebase_admin import credentials, auth

# Load environment variables
load_dotenv()

# Environment Variables
MONGODB_URI = os.getenv('MONGODB_URI')
FIREBASE_CREDENTIALS_JSON = os.getenv('FIREBASE_CREDENTIALS_JSON')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
SMTP_EMAIL = os.getenv('SMTP_EMAIL')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
MASTER_EMAIL = os.getenv('MASTER_EMAIL')
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-flask-secret')

# Database name
DATABASE_NAME = os.getenv('DATABASE_NAME', 'campus_assets')

# Validate required environment variables
required_vars = ['MONGODB_URI', 'FIREBASE_CREDENTIALS_JSON', 'GROQ_API_KEY', 'SMTP_EMAIL', 'SMTP_PASSWORD', 'MASTER_EMAIL']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
    print("Please create a .env file with all required variables")

# MongoDB setup
db = None
try:
    if MONGODB_URI:
        client = MongoClient(MONGODB_URI)
        # Specify database name explicitly
        db = client[DATABASE_NAME]
        # Test connection
        db.command('ping')
        print(f"✅ MongoDB connection successful to database: {DATABASE_NAME}")
    else:
        print("❌ MONGODB_URI not provided")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("Please check your MongoDB connection string")

# Check if Firebase is initialized
try:
    import firebase_admin
    firebase_initialized = firebase_admin._apps and len(firebase_admin._apps) > 0
except Exception:
    firebase_initialized = False

# Firebase setup
try:
    if FIREBASE_CREDENTIALS_JSON and not firebase_initialized:
        # Handle both file path and JSON string
        if os.path.isfile(FIREBASE_CREDENTIALS_JSON):
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_JSON)
        else:
            # Assume it's a JSON string
            firebase_config = json.loads(FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(firebase_config)
        
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
        print("✅ Firebase initialization successful")
    elif firebase_initialized:
        print("✅ Firebase already initialized")
    else:
        print("❌ Firebase credentials not provided")
except Exception as e:
    print(f"❌ Firebase initialization failed: {e}")
    print("Using mock Firebase for testing")

# Constants
ADMIN_ROLE = 'admin'
VIEWER_ROLE = 'viewer'
USER_STATUS_PENDING = 'pending'
USER_STATUS_APPROVED = 'approved'
USER_STATUS_REJECTED = 'rejected'

# Email settings
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

# Resource required fields
RESOURCE_REQUIRED_FIELDS = [
    'sl_no', 'description', 'service_tag', 'identification_number', 
    'procurement_date', 'cost', 'location', 'department'
]

# CSV column mappings
CSV_COLUMN_MAPPING = {
    'SL No': 'sl_no',
    'Description': 'description',
    'Service Tag': 'service_tag',
    'Identification Number': 'identification_number',
    'Procurement Date': 'procurement_date',
    'Cost': 'cost',
    'Location': 'location',
    'Department': 'department'
}

# Collections
USERS_COLLECTION = 'users'
RESOURCES_COLLECTION = 'resources'
SESSIONS_COLLECTION = 'sessions'
CHAT_HISTORY_COLLECTION = 'chat_history'
# Add this section to your config.py

# MongoDB setup with your specific connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://kamalkarteek1:rvZSeyVHhgOd2fbE@gbh.iliw2.mongodb.net/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'campus_assets')

# MongoDB setup
db = None
try:
    if MONGODB_URI:
        client = MongoClient(MONGODB_URI)
        # Use the specific database name
        db = client[DATABASE_NAME]
        # Test connection
        db.command('ping')
        print(f"✅ MongoDB connection successful to database: {DATABASE_NAME}")
        print(f"✅ Available collections: {db.list_collection_names()}")
    else:
        print("❌ MONGODB_URI not provided")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("Please check your MongoDB connection string")

# Collections (make sure these match your database)
USERS_COLLECTION = 'users'
RESOURCES_COLLECTION = 'resources'  # This should match your collection name
SESSIONS_COLLECTION = 'sessions'
CHAT_HISTORY_COLLECTION = 'chat_history'
