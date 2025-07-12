import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Connect to your database
MONGODB_URI = "mongodb+srv://kamalkarteek1:rvZSeyVHhgOd2fbE@gbh.iliw2.mongodb.net/"
DATABASE_NAME = "campus_assets"

try:
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    
    print("🔍 Checking users collection...")
    users = list(db.users.find({}))
    
    print(f"Total users found: {len(users)}")
    
    for user in users:
        print(f"\n--- User ---")
        print(f"Email: {user.get('email')}")
        print(f"Firebase UID: {user.get('firebase_uid')}")
        print(f"Status: {user.get('status')}")
        print(f"Role: {user.get('role')}")
        print(f"Created: {user.get('created_at')}")
        
        # Check what UID would be generated for this email
        email = user.get('email', '')
        expected_uid = f"mock_uid_{email.replace('@', '_').replace('.', '_')}"
        print(f"Expected UID: {expected_uid}")
        print(f"UID Match: {user.get('firebase_uid') == expected_uid}")

except Exception as e:
    print(f"Error: {e}")
