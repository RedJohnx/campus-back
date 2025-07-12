import datetime
import jwt
import uuid
import smtplib
import pandas as pd
import io
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import jsonify, send_file
from bson.objectid import ObjectId
from bson.errors import InvalidId
import requests
import json
from dotenv import load_dotenv
from config import (
    db, ADMIN_ROLE, VIEWER_ROLE, JWT_SECRET, GROQ_API_KEY, 
    SMTP_EMAIL, SMTP_PASSWORD, MASTER_EMAIL, SMTP_SERVER, SMTP_PORT,
    USER_STATUS_PENDING, USER_STATUS_APPROVED, USER_STATUS_REJECTED,
    RESOURCE_REQUIRED_FIELDS, CSV_COLUMN_MAPPING,
    USERS_COLLECTION, RESOURCES_COLLECTION, SESSIONS_COLLECTION, CHAT_HISTORY_COLLECTION
)
from firebase_admin import auth as firebase_auth
from utils import format_response, validate_email, get_user_from_token
load_dotenv()
# Check if Firebase is initialized
try:
    import firebase_admin
    firebase_initialized = firebase_admin._apps and len(firebase_admin._apps) > 0
except Exception:
    firebase_initialized = False

class AuthService:
    def register_user(self, data):
        """Register a new user with Firebase and MongoDB"""
        try:
            # Check if database is available - FIX THIS LINE
            if db is None:
                return format_response(error="Database connection not available", status=500)
            
            email = data.get('email')
            password = data.get('password')
            role = data.get('role', VIEWER_ROLE)
            
            # Validate email format
            if not validate_email(email):
                return format_response(error="Invalid email format", status=400)
            
            # Check if user already exists
            existing_user = db[USERS_COLLECTION].find_one({'email': email})
            if existing_user:
                return format_response(error="User already exists", status=409)
            
            # Create user with Firebase (or mock if Firebase not available)
            user_uid = None
            if firebase_initialized:
                try:
                    user_record = firebase_auth.create_user(
                        email=email,
                        password=password,
                        display_name=data.get('name', ''),
                        email_verified=False
                    )
                    user_uid = user_record.uid
                except Exception as e:
                    print(f"Firebase user creation failed: {e}")
                    # Use mock UID for testing
                    user_uid = f"mock_uid_{email.replace('@', '_').replace('.', '_')}"
                    print(f"🔍 REGISTER DEBUG: Generated UID for {email}: {user_uid}")
                    
                    # Create user document in MongoDB
                    user_doc = {
                        'firebase_uid': user_uid,
                        'email': email,
                        'name': data.get('name', ''),
                        'role': role,
                        'status': USER_STATUS_PENDING if role == ADMIN_ROLE else USER_STATUS_APPROVED,
                        'created_at': datetime.datetime.utcnow(),
                        'last_login': None,
                        'session_ids': []
                    }
                    
                    print(f"🔍 REGISTER DEBUG: Creating user document: {user_doc}")
                    db[USERS_COLLECTION].insert_one(user_doc)
            
            # Send admin verification email if admin role
            if role == ADMIN_ROLE:
                self.send_admin_verification_email(email, data.get('name', ''))
                message = 'Admin account created successfully. Pending approval from master admin.'
            else:
                message = 'User account created successfully.'
            
            return format_response(message=message, status=201)
            
        except Exception as e:
            print(f"Registration error details: {e}")
            return format_response(error=f"Registration failed: {str(e)}", status=400)

    
    def send_admin_verification_email(self, admin_email, admin_name):
        """Send verification email to master admin"""
        try:
            if not SMTP_EMAIL or not SMTP_PASSWORD or not MASTER_EMAIL:
                print("Email configuration not complete, skipping email")
                return
            
            approval_link = f"https://campus-back-production.up.railway.app/admin-verify?email={admin_email}"
            
            msg = MIMEMultipart()
            msg['Subject'] = 'New Admin Account Verification Required'
            msg['From'] = SMTP_EMAIL
            msg['To'] = MASTER_EMAIL
            
            body = f"""
            <html>
            <body>
                <h2>New Admin Account Verification</h2>
                <p>A new admin account has been created and requires your approval:</p>
                <ul>
                    <li><strong>Name:</strong> {admin_name}</li>
                    <li><strong>Email:</strong> {admin_email}</li>
                    <li><strong>Request Date:</strong> {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</li>
                </ul>
                <p>
                    <a href="{approval_link}" 
                       style="background-color: #4CAF50; color: white; padding: 10px 20px; 
                              text-decoration: none; border-radius: 5px;">
                        Approve Admin Account
                    </a>
                </p>
                <p>If you cannot click the link, copy and paste this URL into your browser:</p>
                <p>{approval_link}</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, MASTER_EMAIL, msg.as_string())
            server.quit()
            
            print(f"✅ Admin verification email sent for {admin_email}")
            
        except Exception as e:
            print(f"❌ Failed to send admin verification email: {e}")
    
    def login_user(self, data):
        """Login user with Firebase token or mock token with fallback logic"""
        try:
            print(f"🔍 LOGIN DEBUG: Starting login process")
            print(f"🔍 LOGIN DEBUG: Received data: {data}")
            
            if db is None:
                print(f"❌ LOGIN DEBUG: Database connection is None")
                return format_response(error="Database connection not available", status=500)
            
            id_token = data.get('idToken')
            print(f"🔍 LOGIN DEBUG: ID Token received: {id_token}")
            
            # Extract email from mock token for testing
            if id_token.startswith('simulated_firebase_token_'):
                email = id_token.replace('simulated_firebase_token_', '')
                mock_uid = f"mock_uid_{email.replace('@', '_').replace('.', '_')}"
                print(f"🔍 LOGIN DEBUG: Using mock authentication")
                print(f"🔍 LOGIN DEBUG: Extracted email: {email}")
                print(f"🔍 LOGIN DEBUG: Generated mock UID: {mock_uid}")
                
                # ENHANCED LOGIC: Try multiple approaches to find the user
                user = None
                
                # 1. First try with mock UID
                print(f"🔍 LOGIN DEBUG: Trying to find user with mock UID: {mock_uid}")
                user = db[USERS_COLLECTION].find_one({'firebase_uid': mock_uid})
                
                if not user:
                    print(f"🔍 LOGIN DEBUG: Mock UID not found, trying by email: {email}")
                    # 2. If mock UID fails, try to find by email
                    user = db[USERS_COLLECTION].find_one({'email': email})
                    
                    if user:
                        print(f"✅ LOGIN DEBUG: Found user by email!")
                        print(f"🔍 LOGIN DEBUG: User's current firebase_uid: {user.get('firebase_uid')}")
                        
                        # 3. Update the user's firebase_uid to the mock UID for consistency
                        print(f"🔄 LOGIN DEBUG: Updating user's firebase_uid to mock UID for consistency")
                        db[USERS_COLLECTION].update_one(
                            {'email': email},
                            {'$set': {'firebase_uid': mock_uid}}
                        )
                        # Update the user object to reflect the change
                        user['firebase_uid'] = mock_uid
                        print(f"✅ LOGIN DEBUG: Updated firebase_uid to: {mock_uid}")
                    else:
                        print(f"❌ LOGIN DEBUG: No user found with email: {email}")
                else:
                    print(f"✅ LOGIN DEBUG: Found user with mock UID")
                
                uid = mock_uid  # Use mock UID for session
                
            else:
                # Try to verify with Firebase
                try:
                    if firebase_initialized:
                        decoded_token = firebase_auth.verify_id_token(id_token)
                        uid = decoded_token['uid']
                        email = decoded_token.get('email')
                        print(f"🔍 LOGIN DEBUG: Using Firebase authentication")
                        print(f"🔍 LOGIN DEBUG: Firebase UID: {uid}")
                        print(f"🔍 LOGIN DEBUG: Firebase email: {email}")
                        
                        # Try to find user with Firebase UID
                        user = db[USERS_COLLECTION].find_one({'firebase_uid': uid})
                    else:
                        print(f"❌ LOGIN DEBUG: Firebase not initialized")
                        return format_response(error="Firebase not initialized", status=500)
                except Exception as e:
                    print(f"❌ LOGIN DEBUG: Firebase token verification failed: {str(e)}")
                    return format_response(error=f"Invalid Firebase token: {str(e)}", status=401)
            
            # Final check if user was found
            if not user:
                print(f"❌ LOGIN DEBUG: No user found after all attempts")
                
                # Debug: Show all users again
                all_users = list(db[USERS_COLLECTION].find({}, {'email': 1, 'firebase_uid': 1, 'status': 1, 'role': 1}))
                print(f"🔍 LOGIN DEBUG: All users in database:")
                for u in all_users:
                    print(f"  - Email: {u.get('email')}, UID: {u.get('firebase_uid')}, Status: {u.get('status')}, Role: {u.get('role')}")
                
                return format_response(error="User not found", status=404)
            
            print(f"✅ LOGIN DEBUG: Found user: {user.get('email')}")
            print(f"🔍 LOGIN DEBUG: User status: {user.get('status')}")
            print(f"🔍 LOGIN DEBUG: User firebase_uid: {user.get('firebase_uid')}")
            
            if user['status'] != USER_STATUS_APPROVED:
                print(f"❌ LOGIN DEBUG: User not approved. Status: {user['status']}")
                return format_response(error="Account not approved", status=403)
            
            print(f"✅ LOGIN DEBUG: User is approved, proceeding with login")
            
            # Create session token using the actual UID from database
            actual_uid = user['firebase_uid']
            session_data = {
                'uid': actual_uid,
                'email': user['email'],
                'role': user['role'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
            }
            session_token = jwt.encode(session_data, JWT_SECRET, algorithm='HS256')
            
            # Store session in database
            session_doc = {
                'user_id': actual_uid,
                'session_token': session_token,
                'expires_at': datetime.datetime.utcnow() + datetime.timedelta(hours=8),
                'created_at': datetime.datetime.utcnow(),
                'ip_address': None
            }
            db[SESSIONS_COLLECTION].insert_one(session_doc)
            
            # Update last login
            db[USERS_COLLECTION].update_one(
                {'firebase_uid': actual_uid},
                {'$set': {'last_login': datetime.datetime.utcnow()}}
            )
            
            print(f"✅ LOGIN DEBUG: Login successful for user: {user.get('email')}")
            
            return format_response(
                data={
                    'session_token': session_token,
                    'user': {
                        'uid': actual_uid,
                        'email': user['email'],
                        'name': user.get('name', ''),
                        'role': user['role']
                    }
                },
                message="Login successful",
                status=200
            )
            
        except Exception as e:
            print(f"❌ LOGIN DEBUG: Login error: {str(e)}")
            print(f"❌ LOGIN DEBUG: Error details: {e}")
            return format_response(error=f"Login failed: {str(e)}", status=401)

    
    def verify_admin(self, token):
        """Verify admin account (master admin approval)"""
        try:
            # For simplicity, token is email
            email = token
            
            user = db[USERS_COLLECTION].find_one({'email': email, 'role': ADMIN_ROLE})
            if not user:
                return format_response(error="Admin user not found", status=404)
            
            if user['status'] == USER_STATUS_APPROVED:
                return format_response(message="Admin already approved", status=200)
            
            # Update user status
            db[USERS_COLLECTION].update_one(
                {'email': email},
                {'$set': {'status': USER_STATUS_APPROVED}}
            )
            
            return format_response(message="Admin approved successfully", status=200)
            
        except Exception as e:
            return format_response(error=f"Admin verification failed: {str(e)}", status=400)
    
    def logout_user(self, request):
        """Logout user by invalidating session"""
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return format_response(error="No session token provided", status=400)
            
            session_token = auth_header.split(' ')[1]
            
            # Remove session from database
            result = db[SESSIONS_COLLECTION].delete_one({'session_token': session_token})
            
            if result.deleted_count == 0:
                return format_response(error="Session not found", status=404)
            
            return format_response(message="Logged out successfully", status=200)
            
        except Exception as e:
            return format_response(error=f"Logout failed: {str(e)}", status=400)
    
    def get_user_profile(self, request):
        """Get user profile information"""
        try:
            user_data = get_user_from_token(request)
            if not user_data:
                return format_response(error="Invalid session", status=401)
            
            user = db[USERS_COLLECTION].find_one({'firebase_uid': user_data['uid']})
            if not user:
                return format_response(error="User not found", status=404)
            
            profile_data = {
                'uid': user['firebase_uid'],
                'email': user['email'],
                'name': user.get('name', ''),
                'role': user['role'],
                'status': user['status'],
                'created_at': user['created_at'].isoformat(),
                'last_login': user['last_login'].isoformat() if user['last_login'] else None
            }
            
            return format_response(data=profile_data, status=200)
            
        except Exception as e:
            return format_response(error=f"Failed to fetch profile: {str(e)}", status=400)

# in services.py

import datetime
from bson.objectid import ObjectId
# Assuming you have these defined elsewhere:
# from db import db, RESOURCES_COLLECTION
# from utils import format_response, get_user_from_token
# RESOURCE_REQUIRED_FIELDS = [...]

class ResourceService:

    def get_resources(self, filters, page=1, limit=10):
        """Get resources with enhanced filtering, pagination, and sorting."""
        try:
            query = {}

            # Search functionality (added parent_department)
            search = filters.get('search', '').strip()
            if search:
                query['$or'] = [
                    {'description': {'$regex': search, '$options': 'i'}},
                    {'sl_no': {'$regex': search, '$options': 'i'}},
                    {'service_tag': {'$regex': search, '$options': 'i'}},
                    {'identification_number': {'$regex': search, '$options': 'i'}},
                    {'location': {'$regex': search, '$options': 'i'}},
                    {'department': {'$regex': search, '$options': 'i'}},
                    {'parent_department': {'$regex': search, '$options': 'i'}}
                ]

            # Exact match filtering for dropdowns
            for field in ['location', 'department', 'parent_department']:
                value = filters.get(field)
                if value and value != 'all':
                    query[field] = value # Exact match is better for filters

            # Cost range filtering
            cost_query = {}
            if 'cost_min' in filters and filters['cost_min']:
                try:
                    cost_query['$gte'] = float(filters['cost_min'])
                except (ValueError, TypeError):
                    pass # Ignore invalid number format
            if 'cost_max' in filters and filters['cost_max']:
                try:
                    cost_query['$lte'] = float(filters['cost_max'])
                except (ValueError, TypeError):
                    pass # Ignore invalid number format
            if cost_query:
                query['cost'] = cost_query

            # Calculate pagination
            skip = (page - 1) * limit

            # Get resources and total count
            resources_cursor = db[RESOURCES_COLLECTION].find(query).sort('created_at', -1).skip(skip).limit(limit)
            total = db[RESOURCES_COLLECTION].count_documents(query)
            
            resources = []
            for resource in resources_cursor:
                resource['_id'] = str(resource['_id'])
                # Format dates and ensure all fields are present
                for date_field in ['created_at', 'updated_at']:
                    if date_field in resource and isinstance(resource[date_field], datetime.datetime):
                        resource[date_field] = resource[date_field].isoformat()

                # Ensure all fields exist and have correct types
                resource['sl_no'] = str(resource.get('sl_no', ''))
                resource['description'] = str(resource.get('description', ''))
                resource['service_tag'] = str(resource.get('service_tag', ''))
                resource['identification_number'] = str(resource.get('identification_number', ''))
                resource['procurement_date'] = str(resource.get('procurement_date', ''))
                resource['location'] = str(resource.get('location', ''))
                resource['department'] = str(resource.get('department', ''))
                resource['parent_department'] = str(resource.get('parent_department', ''))
                resource['cost'] = float(resource.get('cost', 0.0))
                resources.append(resource)

            return format_response(
                data={
                    'resources': resources,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total,
                        'pages': (total + limit - 1) // limit if limit > 0 else 0
                    }
                },
                status=200
            )

        except Exception as e:
            print(f"Error getting resources: {e}")
            return format_response(error=f"Failed to fetch resources: {str(e)}", status=500)

    def create_resource(self, data, request):
        """Create a new resource with parent_department."""
        try:
            # Basic Validation
            for field in RESOURCE_REQUIRED_FIELDS:
                if field not in data or not data[field]:
                    return format_response(error=f"Missing required field: {field}", status=400)
            
            user_data = get_user_from_token(request)
            if not user_data:
                return format_response(error="Invalid session", status=401)

            resource_doc = {
                'sl_no': data['sl_no'],
                'description': data['description'],
                'service_tag': data['service_tag'],
                'identification_number': data['identification_number'],
                'procurement_date': data['procurement_date'],
                'cost': float(data['cost']),
                'location': data['location'],
                'department': data['department'],
                'parent_department': data.get('parent_department', ''), # Add new field
                'created_by': user_data['email'],
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow(),
                'updated_by': user_data['email']
            }
            
            result = db[RESOURCES_COLLECTION].insert_one(resource_doc)
            
            return format_response(
                data={'resource_id': str(result.inserted_id)},
                message="Resource created successfully",
                status=201
            )
        except (ValueError, TypeError) as e:
            return format_response(error=f"Invalid data format: {str(e)}", status=400)
        except Exception as e:
            return format_response(error=f"Failed to create resource: {str(e)}", status=500)

    def update_resource(self, resource_id, data, request):
        """Update a resource, including parent_department."""
        try:
            if not ObjectId.is_valid(resource_id):
                return format_response(error="Invalid resource ID", status=400)
            
            user_data = get_user_from_token(request)
            if not user_data:
                return format_response(error="Invalid session", status=401)
            
            # Prepare update data, excluding empty values
            update_data = {k: v for k, v in data.items() if v is not None and v != ''}
            
            if 'cost' in update_data:
                update_data['cost'] = float(update_data['cost'])
            
            update_data['updated_at'] = datetime.datetime.utcnow()
            update_data['updated_by'] = user_data['email']
            
            result = db[RESOURCES_COLLECTION].update_one(
                {'_id': ObjectId(resource_id)},
                {'$set': update_data}
            )
            
            if result.matched_count == 0:
                return format_response(error="Resource not found", status=404)
            
            return format_response(message="Resource updated successfully", status=200)
        except (ValueError, TypeError) as e:
            return format_response(error=f"Invalid data format: {str(e)}", status=400)
        except Exception as e:
            return format_response(error=f"Failed to update resource: {str(e)}", status=500)


    # Other functions (delete_resource, get_resource, dashboard_stats, etc.) remain largely the same.
    # Just ensure they handle the 'parent_department' field if they return resource objects.
    def search_resources(self, query, filters):
        """Enhanced search with multi-field support"""
        try:
            search_query = {}
            
            if query:
                search_query['$or'] = [
                    {'description': {'$regex': query, '$options': 'i'}},
                    {'sl_no': {'$regex': query, '$options': 'i'}},
                    {'service_tag': {'$regex': query, '$options': 'i'}},
                    {'identification_number': {'$regex': query, '$options': 'i'}},
                    {'location': {'$regex': query, '$options': 'i'}},
                    {'section_location': {'$regex': query, '$options': 'i'}},
                    {'product_category': {'$regex': query, '$options': 'i'}},
                    {'department': {'$regex': query, '$options': 'i'}}
                ]
            
            # Apply additional filters
            if 'location' in filters and filters['location']:
                search_query['location'] = {'$regex': filters['location'], '$options': 'i'}
            
            if 'department' in filters and filters['department']:
                search_query['department'] = {'$regex': filters['department'], '$options': 'i'}
            
            if 'product_category' in filters and filters['product_category']:
                search_query['product_category'] = {'$regex': filters['product_category'], '$options': 'i'}
            
            resources = list(db[RESOURCES_COLLECTION].find(search_query).limit(50))
            
            # Convert ObjectId to string
            for resource in resources:
                resource['_id'] = str(resource['_id'])
                if 'created_at' in resource:
                    resource['created_at'] = resource['created_at'].isoformat()
                if 'updated_at' in resource:
                    resource['updated_at'] = resource['updated_at'].isoformat()
            
            return format_response(
                data={
                    'resources': resources,
                    'count': len(resources),
                    'query': query
                },
                status=200
            )
            
        except Exception as e:
            return format_response(error=f"Search failed: {str(e)}", status=400)

    def get_resource(self, resource_id):
        """Get a specific resource"""
        try:
            if not ObjectId.is_valid(resource_id):
                return format_response(error="Invalid resource ID", status=400)
            
            resource = db[RESOURCES_COLLECTION].find_one({'_id': ObjectId(resource_id)})
            if not resource:
                return format_response(error="Resource not found", status=404)
            
            resource['_id'] = str(resource['_id'])
            if 'created_at' in resource:
                resource['created_at'] = resource['created_at'].isoformat()
            if 'updated_at' in resource:
                resource['updated_at'] = resource['updated_at'].isoformat()
            
            return format_response(data=resource, status=200)
            
        except Exception as e:
            return format_response(error=f"Failed to fetch resource: {str(e)}", status=400)
    
    
    def delete_resource(self, resource_id):
        """Delete a resource"""
        try:
            if not ObjectId.is_valid(resource_id):
                return format_response(error="Invalid resource ID", status=400)
            
            result = db[RESOURCES_COLLECTION].delete_one({'_id': ObjectId(resource_id)})
            
            if result.deleted_count == 0:
                return format_response(error="Resource not found", status=404)
            
            return format_response(message="Resource deleted successfully", status=200)
            
        except Exception as e:
            return format_response(error=f"Failed to delete resource: {str(e)}", status=400)
    
    
    def dashboard_stats(self):
        """Get dashboard statistics"""
        try:
            total_resources = db[RESOURCES_COLLECTION].count_documents({})
            
            # Resources by location
            location_stats = list(db[RESOURCES_COLLECTION].aggregate([
                {'$group': {'_id': '$location', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': 10}
            ]))
            
            # Resources by department
            department_stats = list(db[RESOURCES_COLLECTION].aggregate([
                {'$group': {'_id': '$department', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': 10}
            ]))
            
            # Total cost
            total_cost = list(db[RESOURCES_COLLECTION].aggregate([
                {'$group': {'_id': None, 'total': {'$sum': '$cost'}}}
            ]))
            
            total_cost_value = total_cost[0]['total'] if total_cost else 0
            
            # Recent additions (last 7 days)
            week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            recent_additions = db[RESOURCES_COLLECTION].count_documents({
                'created_at': {'$gte': week_ago}
            })
            
            return format_response(
                data={
                    'total_resources': total_resources,
                    'total_cost': total_cost_value,
                    'recent_additions': recent_additions,
                    'location_stats': location_stats,
                    'department_stats': department_stats
                },
                status=200
            )
            
        except Exception as e:
            return format_response(error=f"Failed to fetch dashboard stats: {str(e)}", status=400)
    
    def dashboard_charts(self, chart_type):
        """Get chart data for dashboard"""
        try:
            chart_data = {}
            
            if chart_type in ['all', 'cost_trend']:
                # Cost trend over time
                cost_trend = list(db[RESOURCES_COLLECTION].aggregate([
                    {'$group': {
                        '_id': {
                            'year': {'$year': '$created_at'},
                            'month': {'$month': '$created_at'}
                        },
                        'total_cost': {'$sum': '$cost'},
                        'count': {'$sum': 1}
                    }},
                    {'$sort': {'_id.year': 1, '_id.month': 1}},
                    {'$limit': 12}
                ]))
                chart_data['cost_trend'] = cost_trend
            
            if chart_type in ['all', 'location_distribution']:
                # Location distribution
                location_dist = list(db[RESOURCES_COLLECTION].aggregate([
                    {'$group': {'_id': '$location', 'count': {'$sum': 1}}},
                    {'$sort': {'count': -1}}
                ]))
                chart_data['location_distribution'] = location_dist
            
            if chart_type in ['all', 'department_distribution']:
                # Department distribution
                dept_dist = list(db[RESOURCES_COLLECTION].aggregate([
                    {'$group': {'_id': '$department', 'count': {'$sum': 1}}},
                    {'$sort': {'count': -1}}
                ]))
                chart_data['department_distribution'] = dept_dist
            
            return format_response(data=chart_data, status=200)
            
        except Exception as e:
            return format_response(error=f"Failed to fetch chart data: {str(e)}", status=400)
    
    def recent_activity(self, limit=10):
        """Get recent activity"""
        try:
            recent_resources = list(db[RESOURCES_COLLECTION].find().sort('created_at', -1).limit(limit))
            
            for resource in recent_resources:
                resource['_id'] = str(resource['_id'])
                if 'created_at' in resource:
                    resource['created_at'] = resource['created_at'].isoformat()
                if 'updated_at' in resource:
                    resource['updated_at'] = resource['updated_at'].isoformat()
            
            return format_response(data=recent_resources, status=200)
            
        except Exception as e:
            return format_response(error=f"Failed to fetch recent activity: {str(e)}", status=400)
    
    def get_unique_values(self, field):
        """Get unique, non-empty, sorted values for a given field."""
        try:
            if not field or not isinstance(field, str):
                return format_response(error="Invalid field specified", status=400)
            
            values = db[RESOURCES_COLLECTION].distinct(field)
            # Filter out None, empty strings, and whitespace-only strings
            filtered_values = [val for val in values if val and str(val).strip()]
            
            return format_response(data=sorted(filtered_values), status=200)
        except Exception as e:
            return format_response(error=f"Failed to fetch unique values for '{field}': {str(e)}", status=500)

    def get_filter_options(self):
        """Get all filter options for enhanced filtering"""
        try:
            # Get unique values for all filter fields
            departments = db[RESOURCES_COLLECTION].distinct('department')
            locations = db[RESOURCES_COLLECTION].distinct('location')
            section_locations = db[RESOURCES_COLLECTION].distinct('section_location')
            product_categories = db[RESOURCES_COLLECTION].distinct('product_category')
            
            # Filter out empty values
            departments = [dept for dept in departments if dept and dept.strip()]
            locations = [loc for loc in locations if loc and loc.strip()]
            section_locations = [loc for loc in section_locations if loc and loc.strip()]
            product_categories = [cat for cat in product_categories if cat and cat.strip()]
            
            return format_response(
                data={
                    'departments': sorted(departments),
                    'locations': sorted(locations),
                    'section_locations': sorted(section_locations),
                    'product_categories': sorted(product_categories)
                },
                status=200
            )
            
        except Exception as e:
            return format_response(error=f"Failed to fetch filter options: {str(e)}", status=400)
    
# class AIService:
#     def __init__(self):
#         self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
#         self.headers = {
#             "Authorization": f"Bearer {GROQ_API_KEY}",
#             "Content-Type": "application/json"
#         }
    
#     def natural_crud(self, data, request):
#         """Process natural language CRUD instructions"""
#         try:
#             instruction = data.get('instruction')
#             user_data = get_user_from_token(request)
            
#             # Enhanced parsing prompt with more specific JSON format
#             parsing_prompt = f"""
#     You are a database operation parser. Parse this natural language instruction for resource management:

#     Instruction: "{instruction}"

#     You must respond with ONLY a valid JSON object in this exact format:
#     {{
#         "operation": "CREATE|READ|UPDATE|DELETE",
#         "fields": {{}},
#         "filters": {{}},
#         "missing_fields": [],
#         "resource_id": null
#     }}

#     Rules:
#     - operation: Must be CREATE, READ, UPDATE, or DELETE
#     - fields: Object with field names and values to set/create
#     - filters: Object with criteria to find resources
#     - missing_fields: Array of required fields that are missing
#     - resource_id: String ID if a specific resource is mentioned

#     Required fields for CREATE: sl_no, description, service_tag, identification_number, procurement_date, cost, location, department

#     Examples:
#     - "update cost to 1000 for CSE department" → {{"operation": "UPDATE", "fields": {{"cost": "1000"}}, "filters": {{"department": "CSE"}}, "missing_fields": [], "resource_id": null}}
#     - "create new monitor" → {{"operation": "CREATE", "fields": {{}}, "filters": {{}}, "missing_fields": ["sl_no", "description", "service_tag", "identification_number", "procurement_date", "cost", "location", "department"], "resource_id": null}}

#     Parse: "{instruction}"
#     """
            
#             ai_response = self._call_groq_api(parsing_prompt)
            
#             if not ai_response:
#                 return format_response(error="Failed to get AI response", status=500)
            
#             # Clean the response - remove any non-JSON content
#             try:
#                 # Try to find JSON in the response
#                 import re
#                 json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
#                 if json_match:
#                     json_str = json_match.group()
#                     parsed_data = json.loads(json_str)
#                 else:
#                     # If no JSON found, create a basic structure
#                     parsed_data = {
#                         "operation": "READ",
#                         "fields": {},
#                         "filters": {},
#                         "missing_fields": [],
#                         "resource_id": None
#                     }
                    
#                     # Try to extract operation type from instruction
#                     instruction_lower = instruction.lower()
#                     if any(word in instruction_lower for word in ['create', 'add', 'new']):
#                         parsed_data["operation"] = "CREATE"
#                         parsed_data["missing_fields"] = RESOURCE_REQUIRED_FIELDS
#                     elif any(word in instruction_lower for word in ['update', 'change', 'modify', 'edit']):
#                         parsed_data["operation"] = "UPDATE"
#                         # Try to extract fields from instruction
#                         if 'cost' in instruction_lower:
#                             import re
#                             cost_match = re.search(r'(\d+)', instruction)
#                             if cost_match:
#                                 parsed_data["fields"]["cost"] = cost_match.group(1)
#                         if 'cse' in instruction_lower or 'CSE' in instruction:
#                             parsed_data["filters"]["department"] = "CSE"
#                     elif any(word in instruction_lower for word in ['delete', 'remove']):
#                         parsed_data["operation"] = "DELETE"
                        
#             except json.JSONDecodeError as e:
#                 print(f"JSON parsing error: {e}")
#                 print(f"AI response was: {ai_response}")
                
#                 # Fallback: create a basic response based on instruction keywords
#                 instruction_lower = instruction.lower()
#                 if any(word in instruction_lower for word in ['update', 'change', 'modify']):
#                     parsed_data = {
#                         "operation": "UPDATE",
#                         "fields": {},
#                         "filters": {},
#                         "missing_fields": [],
#                         "resource_id": None
#                     }
                    
#                     # Extract cost if mentioned
#                     import re
#                     cost_match = re.search(r'(\d+)', instruction)
#                     if cost_match:
#                         parsed_data["fields"]["cost"] = cost_match.group(1)
                    
#                     # Extract department if mentioned
#                     if 'cse' in instruction_lower:
#                         parsed_data["filters"]["department"] = "CSE"
#                     elif 'ece' in instruction_lower:
#                         parsed_data["filters"]["department"] = "ECE"
#                     elif 'eee' in instruction_lower:
#                         parsed_data["filters"]["department"] = "EEE"
                        
#                 else:
#                     return format_response(
#                         error=f"Could not parse instruction. AI response: {ai_response[:200]}...", 
#                         status=500
#                     )
            
#             # Validate the parsed data structure
#             if not isinstance(parsed_data, dict):
#                 return format_response(error="Invalid response structure", status=500)
                
#             # Ensure required keys exist
#             required_keys = ["operation", "fields", "filters", "missing_fields", "resource_id"]
#             for key in required_keys:
#                 if key not in parsed_data:
#                     parsed_data[key] = [] if key == "missing_fields" else ({} if key in ["fields", "filters"] else None)
            
#             # Check for missing fields
#             if parsed_data.get('missing_fields'):
#                 return format_response(
#                     data={
#                         'missing_fields': parsed_data['missing_fields'],
#                         'message': f"Please provide the following fields: {', '.join(parsed_data['missing_fields'])}"
#                     },
#                     status=400
#                 )
            
#             # Execute the operation
#             operation = parsed_data.get('operation', '').upper()
            
#             if operation == 'CREATE':
#                 return self._execute_create(parsed_data.get('fields', {}), user_data)
#             elif operation == 'READ':
#                 return self._execute_read(parsed_data.get('filters', {}))
#             elif operation == 'UPDATE':
#                 return self._execute_update_bulk(
#                     parsed_data.get('filters', {}),
#                     parsed_data.get('fields', {}),
#                     user_data
#                 )
#             elif operation == 'DELETE':
#                 return self._execute_delete_bulk(parsed_data.get('filters', {}))
#             else:
#                 return format_response(error=f"Unknown operation: {operation}", status=400)
            
#         except Exception as e:
#             print(f"Natural CRUD error: {e}")
#             return format_response(error=f"Natural CRUD failed: {str(e)}", status=500)

#     def _call_groq_api(self, prompt):
#         """Call Groq API with better error handling"""
#         try:
#             payload = {
#                 "model": "llama3-8b-8192",
#                 "messages": [
#                     {
#                         "role": "system", 
#                         "content": "You are a precise database operation parser. Always respond with valid JSON only."
#                     },
#                     {
#                         "role": "user", 
#                         "content": prompt
#                     }
#                 ],
#                 "max_tokens": 500,
#                 "temperature": 0.1
#             }
            
#             response = requests.post(self.groq_url, headers=self.headers, json=payload, timeout=30)
#             response.raise_for_status()
            
#             result = response.json()
#             if 'choices' in result and len(result['choices']) > 0:
#                 return result['choices'][0]['message']['content'].strip()
#             else:
#                 print(f"Unexpected Groq response structure: {result}")
#                 return None
                
#         except requests.exceptions.Timeout:
#             print("Groq API timeout")
#             return None
#         except requests.exceptions.RequestException as e:
#             print(f"Groq API request error: {e}")
#             return None
#         except Exception as e:
#             print(f"Groq API error: {e}")
#             return None

#     def _execute_create(self, fields, user_data):
#         """Execute CREATE operation"""
#         try:
#             resource_doc = {
#                 'sl_no': fields.get('sl_no'),
#                 'description': fields.get('description'),
#                 'service_tag': fields.get('service_tag'),
#                 'identification_number': fields.get('identification_number'),
#                 'procurement_date': fields.get('procurement_date'),
#                 'cost': float(fields.get('cost', 0)),
#                 'location': fields.get('location'),
#                 'department': fields.get('department'),
#                 'created_by': user_data['email'],
#                 'created_at': datetime.datetime.utcnow(),
#                 'updated_at': datetime.datetime.utcnow()
#             }
            
#             result = db[RESOURCES_COLLECTION].insert_one(resource_doc)
            
#             return format_response(
#                 data={'resource_id': str(result.inserted_id)},
#                 message="Resource created successfully via AI",
#                 status=201
#             )
            
#         except Exception as e:
#             return format_response(error=f"Create operation failed: {str(e)}", status=400)
    
#     def _execute_read(self, filters):
#         """Execute READ operation"""
#         try:
#             query = {}
#             for key, value in filters.items():
#                 if key in ['location', 'department', 'description']:
#                     query[key] = {'$regex': value, '$options': 'i'}
#                 else:
#                     query[key] = value
            
#             resources = list(db[RESOURCES_COLLECTION].find(query).limit(10))
            
#             for resource in resources:
#                 resource['_id'] = str(resource['_id'])
#                 if 'created_at' in resource:
#                     resource['created_at'] = resource['created_at'].isoformat()
#                 if 'updated_at' in resource:
#                     resource['updated_at'] = resource['updated_at'].isoformat()
            
#             return format_response(data=resources, status=200)
            
#         except Exception as e:
#             return format_response(error=f"Read operation failed: {str(e)}", status=400)
    
#     def _execute_update(self, resource_id, fields, user_data):
#         """Execute UPDATE operation"""
#         try:
#             if not resource_id or not ObjectId.is_valid(resource_id):
#                 return format_response(error="Invalid resource ID", status=400)
            
#             update_data = {k: v for k, v in fields.items() if v is not None}
#             if 'cost' in update_data:
#                 update_data['cost'] = float(update_data['cost'])
            
#             update_data['updated_at'] = datetime.datetime.utcnow()
#             update_data['updated_by'] = user_data['email']
            
#             result = db[RESOURCES_COLLECTION].update_one(
#                 {'_id': ObjectId(resource_id)},
#                 {'$set': update_data}
#             )
            
#             if result.matched_count == 0:
#                 return format_response(error="Resource not found", status=404)
            
#             return format_response(message="Resource updated successfully via AI", status=200)
            
#         except Exception as e:
#             return format_response(error=f"Update operation failed: {str(e)}", status=400)
    
#     def _execute_delete(self, resource_id):
#         """Execute DELETE operation"""
#         try:
#             if not resource_id or not ObjectId.is_valid(resource_id):
#                 return format_response(error="Invalid resource ID", status=400)
            
#             result = db[RESOURCES_COLLECTION].delete_one({'_id': ObjectId(resource_id)})
            
#             if result.deleted_count == 0:
#                 return format_response(error="Resource not found", status=404)
            
#             return format_response(message="Resource deleted successfully via AI", status=200)
            
#         except Exception as e:
#             return format_response(error=f"Delete operation failed: {str(e)}", status=400)
    
#     def chat(self, data, request):
#         """Handle chat queries about resources"""
#         try:
#             message = data.get('message')
#             user_data = get_user_from_token(request)
            
#             # Get context about resources
#             context = self._get_resource_context()
            
#             # Create chat prompt
#             chat_prompt = f"""
#             You are a resource management assistant. Answer questions about the resources based on the following context:
            
#             Context: {context}
            
#             User question: {message}
            
#             Provide a helpful and accurate response about the resources. If you need specific data that's not in the context, ask for clarification.
#             """
            
#             ai_response = self._call_groq_api(chat_prompt)
            
#             if not ai_response:
#                 return format_response(error="Failed to get response", status=500)
            
#             # Save chat history
#             chat_doc = {
#                 'user_id': user_data['uid'],
#                 'message': message,
#                 'response': ai_response,
#                 'timestamp': datetime.datetime.utcnow()
#             }
            
#             db[CHAT_HISTORY_COLLECTION].insert_one(chat_doc)
            
#             return format_response(
#                 data={
#                     'response': ai_response,
#                     'timestamp': datetime.datetime.utcnow().isoformat()
#                 },
#                 status=200
#             )
            
#         except Exception as e:
#             return format_response(error=f"Chat failed: {str(e)}", status=500)
    
#     def _get_resource_context(self):
#         """Get context about current resources"""
#         try:
#             total_resources = db[RESOURCES_COLLECTION].count_documents({})
            
#             # Get sample resources
#             sample_resources = list(db[RESOURCES_COLLECTION].find().limit(5))
            
#             # Get stats
#             locations = db[RESOURCES_COLLECTION].distinct('location')
#             departments = db[RESOURCES_COLLECTION].distinct('department')
            
#             context = {
#                 'total_resources': total_resources,
#                 'locations': locations,
#                 'departments': departments,
#                 'sample_resources': [
#                     {
#                         'description': r.get('description'),
#                         'location': r.get('location'),
#                         'department': r.get('department'),
#                         'cost': r.get('cost')
#                     } for r in sample_resources
#                 ]
#             }
            
#             return json.dumps(context, indent=2)
            
#         except Exception as e:
#             return "No resource context available"
    
#     def chat_history(self, user_id, page, limit, request):
#         """Get chat history"""
#         try:
#             user_data = get_user_from_token(request)
            
#             # If no user_id provided, use current user
#             if not user_id:
#                 user_id = user_data['uid']
            
#             # Check if user can access this history
#             if user_data['role'] != ADMIN_ROLE and user_id != user_data['uid']:
#                 return format_response(error="Access denied", status=403)
            
#             skip = (page - 1) * limit
            
#             history = list(db[CHAT_HISTORY_COLLECTION].find(
#                 {'user_id': user_id}
#             ).sort('timestamp', -1).skip(skip).limit(limit))
            
#             for chat in history:
#                 chat['_id'] = str(chat['_id'])
#                 chat['timestamp'] = chat['timestamp'].isoformat()
            
#             return format_response(data=history, status=200)
            
#         except Exception as e:
#             return format_response(error=f"Failed to fetch chat history: {str(e)}", status=400)
#     def _execute_update_bulk(self, filters, fields, user_data):
#         """Execute UPDATE operation on multiple resources"""
#         try:
#             if not filters:
#                 return format_response(error="No filters provided for update", status=400)
            
#             if not fields:
#                 return format_response(error="No fields provided for update", status=400)
            
#             # Build query from filters
#             query = {}
#             for key, value in filters.items():
#                 if key in ['location', 'department', 'description']:
#                     query[key] = {'$regex': value, '$options': 'i'}
#                 else:
#                     query[key] = value
            
#             # Prepare update data
#             update_data = {k: v for k, v in fields.items() if v is not None}
#             if 'cost' in update_data:
#                 update_data['cost'] = float(update_data['cost'])
            
#             update_data['updated_at'] = datetime.datetime.utcnow()
#             update_data['updated_by'] = user_data['email']
            
#             # Update resources
#             result = db[RESOURCES_COLLECTION].update_many(query, {'$set': update_data})
            
#             return format_response(
#                 data={
#                     'matched_count': result.matched_count,
#                     'modified_count': result.modified_count,
#                     'filters_used': filters,
#                     'fields_updated': fields
#                 },
#                 message=f"Updated {result.modified_count} resources via AI",
#                 status=200
#             )
            
#         except Exception as e:
#             return format_response(error=f"Bulk update operation failed: {str(e)}", status=400)

#     def _execute_delete_bulk(self, filters):
#         """Execute DELETE operation on multiple resources"""
#         try:
#             if not filters:
#                 return format_response(error="No filters provided for delete", status=400)
            
#             # Build query from filters
#             query = {}
#             for key, value in filters.items():
#                 if key in ['location', 'department', 'description']:
#                     query[key] = {'$regex': value, '$options': 'i'}
#                 else:
#                     query[key] = value
            
#             # Count resources to be deleted
#             count = db[RESOURCES_COLLECTION].count_documents(query)
            
#             if count == 0:
#                 return format_response(error="No resources found matching the criteria", status=404)
            
#             # Delete resources
#             result = db[RESOURCES_COLLECTION].delete_many(query)
            
#             return format_response(
#                 data={
#                     'deleted_count': result.deleted_count,
#                     'filters_used': filters
#                 },
#                 message=f"Deleted {result.deleted_count} resources via AI",
#                 status=200
#             )
            
#         except Exception as e:
#             return format_response(error=f"Bulk delete operation failed: {str(e)}", status=400)
class AIService:
    def __init__(self):
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        self.max_context_resources = 20  # Limit context to 20 most relevant resources

    def _analyze_user_query(self, message):
        """Analyze user query to determine what data is needed"""
        message_lower = message.lower()
        
        # Determine query type and filters
        query_analysis = {
            'needs_specific_data': False,
            'query_filters': {},
            'context_type': 'summary',  # summary, specific, search
            'keywords': []
        }
        
        # Extract departments
        dept_keywords = {
            'cse': 'Computer Science and Engineering',
            'computer': 'Computer Science and Engineering',
            'ece': 'Electronics and Communication Engineering',
            'electronics': 'Electronics and Instrumentation Engineering',
            'mechanical': 'Mechanical Engineering',
            'civil': 'Civil Engineering'
        }
        
        for keyword, dept in dept_keywords.items():
            if keyword in message_lower:
                query_analysis['query_filters']['department'] = dept
                query_analysis['needs_specific_data'] = True
                break
        
        # Extract locations
        location_keywords = ['laboratory', 'lab', 'facility', 'centre', 'center', 'computing', 'workshop']
        for keyword in location_keywords:
            if keyword in message_lower:
                query_analysis['keywords'].append(keyword)
                query_analysis['needs_specific_data'] = True
        
        # Extract cost-related queries
        if any(word in message_lower for word in ['cost', 'price', 'expensive', 'cheap', 'budget']):
            query_analysis['context_type'] = 'cost_analysis'
            query_analysis['needs_specific_data'] = True
        
        # Extract search terms
        search_keywords = ['show', 'find', 'search', 'list', 'get']
        for keyword in search_keywords:
            if keyword in message_lower:
                query_analysis['context_type'] = 'search'
                query_analysis['needs_specific_data'] = True
                break
        
        return query_analysis

    def _get_smart_context(self, message):
        """Get intelligent context based on user query instead of all resources"""
        try:
            if db is None:
                return json.dumps({"error": "Database connection not available"})
            
            # Analyze what the user is asking for
            analysis = self._analyze_user_query(message)
            
            # Get basic statistics (always included, lightweight)
            total_resources = db[RESOURCES_COLLECTION].count_documents({})
            
            # Build query based on analysis
            query = {}
            if analysis['query_filters']:
                query.update(analysis['query_filters'])
            
            # Add keyword search if needed
            if analysis['keywords']:
                keyword_regex = '|'.join(analysis['keywords'])
                query['$or'] = [
                    {'description': {'$regex': keyword_regex, '$options': 'i'}},
                    {'location': {'$regex': keyword_regex, '$options': 'i'}},
                    {'section_location': {'$regex': keyword_regex, '$options': 'i'}},
                    {'product_category': {'$regex': keyword_regex, '$options': 'i'}}
                ]
            
            # Determine what data to fetch based on context type
            if analysis['context_type'] == 'summary':
                context = self._get_summary_context()
            elif analysis['context_type'] == 'cost_analysis':
                context = self._get_cost_context(query)
            elif analysis['context_type'] == 'search' or analysis['needs_specific_data']:
                context = self._get_filtered_context(query, message)
            else:
                context = self._get_summary_context()
            
            context['query_analysis'] = analysis
            context['total_resources'] = total_resources
            context['context_size'] = 'optimized'
            
            return json.dumps(context, indent=2, default=str)
            
        except Exception as e:
            print(f"Error getting smart context: {e}")
            return json.dumps({
                "error": str(e), 
                "total_resources": 0, 
                "relevant_resources": []
            })

    def _get_summary_context(self):
        """Get lightweight summary context"""
        try:
            # Get department statistics
            dept_stats = list(db[RESOURCES_COLLECTION].aggregate([
                {'$group': {'_id': '$department', 'count': {'$sum': 1}, 'total_cost': {'$sum': '$cost'}}},
                {'$sort': {'count': -1}}
            ]))
            
            # Get location statistics  
            location_stats = list(db[RESOURCES_COLLECTION].aggregate([
                {'$group': {'_id': '$location', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': 10}
            ]))
            
            # Get recent additions (last 5)
            recent_resources = list(db[RESOURCES_COLLECTION].find({}, {
                'description': 1, 'department': 1, 'cost': 1, 'created_at': 1
            }).sort('created_at', -1).limit(5))
            
            return {
                'context_type': 'summary',
                'department_statistics': dept_stats,
                'location_statistics': location_stats,
                'recent_resources': recent_resources,
                'sample_size': len(recent_resources)
            }
            
        except Exception as e:
            print(f"Error in summary context: {e}")
            return {'context_type': 'summary', 'error': str(e)}

    def _get_cost_context(self, base_query):
        """Get cost-focused context"""
        try:
            # Most expensive items
            expensive_items = list(db[RESOURCES_COLLECTION].find(
                base_query, 
                {'description': 1, 'cost': 1, 'department': 1, 'location': 1}
            ).sort('cost', -1).limit(10))
            
            # Cost distribution by department
            cost_by_dept = list(db[RESOURCES_COLLECTION].aggregate([
                {'$match': base_query},
                {'$group': {'_id': '$department', 'total_cost': {'$sum': '$cost'}, 'avg_cost': {'$avg': '$cost'}, 'count': {'$sum': 1}}},
                {'$sort': {'total_cost': -1}}
            ]))
            
            return {
                'context_type': 'cost_analysis',
                'expensive_items': expensive_items,
                'cost_by_department': cost_by_dept,
                'sample_size': len(expensive_items)
            }
            
        except Exception as e:
            print(f"Error in cost context: {e}")
            return {'context_type': 'cost_analysis', 'error': str(e)}

    def _get_filtered_context(self, query, message):
        """Get filtered context based on specific query"""
        try:
            # Limit to most relevant resources
            relevant_resources = list(db[RESOURCES_COLLECTION].find(
                query,
                {
                    'sl_no': 1, 'description': 1, 'cost': 1, 
                    'department': 1, 'location': 1, 'section_location': 1,
                    'product_category': 1, 'created_at': 1
                }
            ).limit(self.max_context_resources))
            
            # Get summary stats for the filtered data
            if query:
                filtered_stats = list(db[RESOURCES_COLLECTION].aggregate([
                    {'$match': query},
                    {'$group': {
                        '_id': None, 
                        'total_cost': {'$sum': '$cost'},
                        'count': {'$sum': 1},
                        'avg_cost': {'$avg': '$cost'}
                    }}
                ]))
            else:
                filtered_stats = []
            
            return {
                'context_type': 'filtered',
                'relevant_resources': relevant_resources,
                'filtered_statistics': filtered_stats[0] if filtered_stats else {},
                'sample_size': len(relevant_resources),
                'query_used': query
            }
            
        except Exception as e:
            print(f"Error in filtered context: {e}")
            return {'context_type': 'filtered', 'error': str(e)}

    def chat(self, data, request):
        """Enhanced chat with smart context selection"""
        try:
            message = data.get('message')
            user_data = get_user_from_token(request)
            
            if db is None:
                return format_response(error="Database connection not available", status=500)
            
            # Get smart, optimized context instead of all resources
            context = self._get_smart_context(message)
            context_data = json.loads(context)
            
            # Create focused chat prompt
            chat_prompt = f"""
You are a professional campus assets management assistant. 

=== OPTIMIZED CONTEXT (Not all data, only relevant) ===
{context}

=== USER QUESTION ===
{message}

=== RESPONSE INSTRUCTIONS ===
1. **Be ACCURATE**: Use ONLY the provided context data
2. **Be SPECIFIC**: Reference actual items and details
3. **Use Emojis**: Make responses engaging
4. **Format Well**: Use markdown formatting
5. **Stay Focused**: Answer based on the relevant context provided

Note: If you need more specific data that's not in the context, suggest what the user should ask for.
"""

            ai_response = self._call_groq_api(chat_prompt)
            
            if not ai_response:
                return format_response(error="Failed to get AI response", status=500)
            
            # Save chat history
            try:
                chat_doc = {
                    'user_id': user_data['uid'],
                    'message': message,
                    'response': ai_response,
                    'timestamp': datetime.datetime.utcnow(),
                    'context_type': context_data.get('context_type', 'unknown'),
                    'context_size': context_data.get('sample_size', 0)
                }
                db[CHAT_HISTORY_COLLECTION].insert_one(chat_doc)
            except Exception as e:
                print(f"Failed to save chat history: {e}")
            
            return format_response(
                data={
                    'response': ai_response,
                    'timestamp': datetime.datetime.utcnow().isoformat(),
                    'context_type': context_data.get('context_type'),
                    'resources_analyzed': context_data.get('sample_size', 0)
                },
                status=200
            )
            
        except Exception as e:
            print(f"Chat error: {e}")
            return format_response(error=f"Chat failed: {str(e)}", status=500)

    def _call_groq_api(self, prompt):
        """Enhanced Groq API call with token management"""
        try:
            payload = {
                "model": "llama3-8b-8192",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional campus asset management assistant. Provide helpful, concise responses using markdown formatting."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": 1500,  # Reasonable limit
                "temperature": 0.1,
                "top_p": 0.9
            }
            
            response = requests.post(
                self.groq_url,
                headers=self.headers, 
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content'].strip()
            else:
                print(f"Unexpected Groq response: {result}")
                return None
                
        except requests.exceptions.HTTPError as e:
            print(f"Groq API HTTP error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            return None
        except Exception as e:
            print(f"Groq API error: {e}")
            return None

    # Keep your existing natural_crud and other methods with similar optimizations
    # ... (rest of the methods remain the same but apply similar context optimization)

    def natural_crud(self, data, request):
        """Process natural language CRUD instructions using smart context (optimized, not full DB dump)"""
        try:
            instruction = data.get('instruction')
            user_data = get_user_from_token(request)

            if db is None:
                return format_response(error="Database connection not available", status=500)

            # Use smart, optimized context for the instruction (not all resources)
            context = self._get_smart_context(instruction)
            context_data = json.loads(context)

            # Enhanced parsing prompt with smart context
            parsing_prompt = f"""
You are an advanced database operation parser for a Campus Assets Management System.

=== OPTIMIZED CONTEXT (Not all data, only relevant) ===
{context}

=== USER INSTRUCTION ===
"{instruction}"

Analyze the instruction and respond with ONLY a valid JSON object in this exact format:
{{
    "operation": "CREATE|READ|UPDATE|DELETE",
    "fields": {{}},
    "filters": {{}},
    "missing_fields": [],
    "resource_id": null,
    "confidence": "high|medium|low",
    "estimated_affected_records": 0
}}

Rules:
- For UPDATE: Use "filters" to find resources and "fields" for new values
- For READ: Use "filters" to search
- For CREATE: Put all new data in "fields"
- For DELETE: Use "filters" to identify resources to delete
- If "last entered item" is mentioned, use the most recent created_at timestamp
- Be precise with numbers and exact matches

Examples:
- "update cost of last entered item to 500000" → {{"operation": "UPDATE", "filters": {{"created_at": "latest"}}, "fields": {{"cost": 500000}}}}
- "show items in CSE department" → {{"operation": "READ", "filters": {{"department": "CSE"}}}}
"""

            ai_response = self._call_groq_api(parsing_prompt)

            if not ai_response:
                return format_response(error="Failed to process instruction with AI", status=500)

            # Extract JSON more reliably
            try:
                cleaned_response = ai_response.strip()
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    parsed_data = json.loads(json_str)
                else:
                    raise ValueError("No valid JSON found in AI response")
            except (json.JSONDecodeError, ValueError) as e:
                return format_response(
                    error=f"Could not parse AI response: {str(e)}",
                    data={'ai_response': ai_response[:500]},
                    status=500
                )

            # Validate parsed data structure
            required_keys = ["operation", "fields", "filters", "missing_fields"]
            for key in required_keys:
                if key not in parsed_data:
                    parsed_data[key] = [] if key == "missing_fields" else {}

            # Handle "latest" filter for last entered item
            if parsed_data.get('filters', {}).get('created_at') == 'latest':
                latest_resource = db[RESOURCES_COLLECTION].find().sort('created_at', -1).limit(1)
                latest_resource = list(latest_resource)
                if latest_resource:
                    parsed_data['filters'] = {'_id': latest_resource[0]['_id']}
                else:
                    return format_response(error="No resources found in database", status=404)

            # Execute the operation based on parsed data
            operation = parsed_data.get('operation', '').upper()
            try:
                if operation == 'CREATE':
                    result = self._execute_create(parsed_data.get('fields', {}), user_data)
                elif operation == 'READ':
                    result = self._execute_read(parsed_data.get('filters', {}))
                elif operation == 'UPDATE':
                    result = self._execute_update_bulk(
                        parsed_data.get('filters', {}),
                        parsed_data.get('fields', {}),
                        user_data
                    )
                elif operation == 'DELETE':
                    result = self._execute_delete_bulk(parsed_data.get('filters', {}))
                else:
                    return format_response(
                        error=f"Unsupported operation: {operation}",
                        status=400
                    )
                return result
            except Exception as e:
                return format_response(
                    error=f"Operation execution failed: {str(e)}",
                    data={
                        'operation': operation,
                        'instruction': instruction
                    },
                    status=500
                )

        except Exception as e:
            print(f"Natural CRUD error: {e}")
            return format_response(error=f"Natural CRUD processing failed: {str(e)}", status=500)

    def _call_groq_api(self, prompt):
        """Enhanced Groq API call with better error handling and retry logic"""
        try:
            payload = {
                "model": "llama3-8b-8192",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a professional assistant for campus asset management. Provide detailed, well-formatted responses using markdown. Be precise and helpful."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": 2000,  # Increased for more detailed responses
                "temperature": 0.1,
                "top_p": 0.9
            }
            
            response = requests.post(
                self.groq_url, 
                headers=self.headers, 
                json=payload, 
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"Groq API response structure: {result}")  # Debug line
            
            if 'choices' in result and len(result['choices']) > 0:
                # FIX: choices is a list, so access the first element with [0]
                return result['choices'][0]['message']['content'].strip()
            else:
                print(f"Unexpected Groq response structure: {result}")
                return None
                
        except requests.exceptions.Timeout:
            print("Groq API timeout")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"Groq API HTTP error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Groq API request error: {e}")
            return None
        except Exception as e:
            print(f"Groq API unexpected error: {e}")
            return None

    
    def _execute_create(self, fields, user_data):
        """Execute CREATE operation with validation"""
        try:
            # Validate required fields
            required_fields = ['sl_no', 'description', 'service_tag', 'identification_number', 'procurement_date', 'cost', 'location', 'department']
            missing_fields = [field for field in required_fields if field not in fields or not fields[field]]
            
            if missing_fields:
                return format_response(
                    error=f"Missing required fields: {', '.join(missing_fields)}",
                    status=400
                )
            
            # Prepare resource document
            resource_doc = {
                'sl_no': str(fields['sl_no']),
                'description': fields['description'],
                'service_tag': fields['service_tag'],
                'identification_number': fields['identification_number'],
                'procurement_date': fields['procurement_date'],
                'cost': float(fields['cost']),
                'location': fields['location'],
                'department': fields['department'],
                'created_by': user_data['email'],
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow()
            }
            
            # Insert resource
            result = db[RESOURCES_COLLECTION].insert_one(resource_doc)
            
            return format_response(
                data={
                    'resource_id': str(result.inserted_id),
                    'created_resource': resource_doc
                },
                message=f"## ✅ Resource Created Successfully\n\n**Resource ID:** {str(result.inserted_id)}\n**Description:** {fields['description']}\n**Department:** {fields['department']}\n**Location:** {fields['location']}\n**Cost:** ₹{fields['cost']:,.2f}",
                status=201
            )
            
        except Exception as e:
            return format_response(error=f"Create operation failed: {str(e)}", status=400)
    
    def _execute_read(self, filters):
        """Execute READ operation with enhanced formatting"""
        try:
            # Build query from filters
            query = {}
            for key, value in filters.items():
                if key in ['location', 'department', 'description']:
                    query[key] = {'$regex': value, '$options': 'i'}
                elif key == 'cost':
                    try:
                        query[key] = float(value)
                    except:
                        query[key] = {'$regex': str(value), '$options': 'i'}
                else:
                    query[key] = value
            
            # Get resources
            resources = list(db[RESOURCES_COLLECTION].find(query).limit(50))
            
            # Format resources for display
            formatted_resources = []
            total_cost = 0
            
            for resource in resources:
                formatted_resource = {
                    'id': str(resource['_id']),
                    'sl_no': resource.get('sl_no'),
                    'description': resource.get('description'),
                    'service_tag': resource.get('service_tag'),
                    'identification_number': resource.get('identification_number'),
                    'procurement_date': resource.get('procurement_date'),
                    'cost': float(resource.get('cost', 0)),
                    'location': resource.get('location'),
                    'department': resource.get('department'),
                    'created_at': resource.get('created_at').isoformat() if resource.get('created_at') else None,
                    'updated_at': resource.get('updated_at').isoformat() if resource.get('updated_at') else None
                }
                formatted_resources.append(formatted_resource)
                total_cost += formatted_resource['cost']
            
            # Create formatted message
            if len(resources) == 0:
                message = "## 🔍 No Resources Found\n\nNo resources match the specified criteria."
            else:
                message = f"## 📋 Found {len(resources)} Resource(s)\n\n"
                message += f"**Total Value:** ₹{total_cost:,.2f}\n\n"
                
                if len(resources) <= 10:
                    message += "### Resource Details:\n\n"
                    for i, resource in enumerate(formatted_resources, 1):
                        message += f"**{i}. {resource['description']}**\n"
                        message += f"   - **SL No:** {resource['sl_no']}\n"
                        message += f"   - **Department:** {resource['department']}\n"
                        message += f"   - **Location:** {resource['location']}\n"
                        message += f"   - **Cost:** ₹{resource['cost']:,.2f}\n"
                        message += f"   - **Service Tag:** {resource['service_tag']}\n\n"
                else:
                    message += f"### Summary (showing first 10 of {len(resources)} resources):\n\n"
                    for i, resource in enumerate(formatted_resources[:10], 1):
                        message += f"{i}. **{resource['description']}** - {resource['department']} - ₹{resource['cost']:,.2f}\n"
            
            return format_response(
                data=formatted_resources,
                message=message,
                status=200
            )
            
        except Exception as e:
            return format_response(error=f"Read operation failed: {str(e)}", status=400)
    
    def _execute_update_bulk(self, filters, fields, user_data):
        """Execute bulk UPDATE operation with detailed feedback"""
        try:
            if not filters:
                return format_response(error="No filters provided for update operation", status=400)
            
            if not fields:
                return format_response(error="No fields provided for update operation", status=400)
            
            # Build query from filters
            query = {}
            for key, value in filters.items():
                if key in ['location', 'department', 'description']:
                    query[key] = {'$regex': value, '$options': 'i'}
                else:
                    query[key] = value
            
            # Prepare update data
            update_data = {k: v for k, v in fields.items() if v is not None}
            if 'cost' in update_data:
                update_data['cost'] = float(update_data['cost'])
            
            update_data['updated_at'] = datetime.datetime.utcnow()
            update_data['updated_by'] = user_data['email']
            
            # Get resources that will be updated (for reporting)
            resources_to_update = list(db[RESOURCES_COLLECTION].find(query))
            
            # Update resources
            result = db[RESOURCES_COLLECTION].update_many(query, {'$set': update_data})
            
            # Create detailed message
            message = f"## ✅ Bulk Update Completed\n\n"
            message += f"**Resources Updated:** {result.modified_count} out of {result.matched_count} matched\n"
            message += f"**Fields Updated:** {', '.join(fields.keys())}\n\n"
            
            if result.modified_count > 0 and len(resources_to_update) <= 10:
                message += "### Updated Resources:\n\n"
                for i, resource in enumerate(resources_to_update[:result.modified_count], 1):
                    message += f"{i}. **{resource.get('description')}** ({resource.get('department')})\n"
            
            return format_response(
                data={
                    'matched_count': result.matched_count,
                    'modified_count': result.modified_count,
                    'filters_used': filters,
                    'fields_updated': fields,
                    'updated_resources': [str(r['_id']) for r in resources_to_update[:result.modified_count]]
                },
                message=message,
                status=200
            )
            
        except Exception as e:
            return format_response(error=f"Bulk update operation failed: {str(e)}", status=400)
    
    def _execute_delete_bulk(self, filters):
        """Execute bulk DELETE operation with detailed feedback"""
        try:
            if not filters:
                return format_response(error="No filters provided for delete operation", status=400)
            
            # Build query from filters
            query = {}
            for key, value in filters.items():
                if key in ['location', 'department', 'description']:
                    query[key] = {'$regex': value, '$options': 'i'}
                else:
                    query[key] = value
            
            # Get resources that will be deleted (for reporting)
            resources_to_delete = list(db[RESOURCES_COLLECTION].find(query))
            
            if len(resources_to_delete) == 0:
                return format_response(
                    error="No resources found matching the delete criteria",
                    status=404
                )
            
            # Delete resources
            result = db[RESOURCES_COLLECTION].delete_many(query)
            
            # Create detailed message
            message = f"## ⚠️ Bulk Delete Completed\n\n"
            message += f"**Resources Deleted:** {result.deleted_count}\n\n"
            
            if len(resources_to_delete) <= 10:
                message += "### Deleted Resources:\n\n"
                for i, resource in enumerate(resources_to_delete, 1):
                    message += f"{i}. **{resource.get('description')}** - {resource.get('department')} - ₹{resource.get('cost', 0):,.2f}\n"
            
            return format_response(
                data={
                    'deleted_count': result.deleted_count,
                    'filters_used': filters,
                    'deleted_resources': [
                        {
                            'id': str(r['_id']),
                            'description': r.get('description'),
                            'department': r.get('department'),
                            'cost': r.get('cost')
                        } for r in resources_to_delete
                    ]
                },
                message=message,
                status=200
            )
            
        except Exception as e:
            return format_response(error=f"Bulk delete operation failed: {str(e)}", status=400)
    
    def chat_history(self, user_id, page, limit, request):
        """Get chat history with enhanced formatting"""
        try:
            user_data = get_user_from_token(request)
            
            # If no user_id provided, use current user
            if not user_id:
                user_id = user_data['uid']
            
            # Check if user can access this history
            if user_data['role'] != ADMIN_ROLE and user_id != user_data['uid']:
                return format_response(error="Access denied", status=403)
            
            skip = (page - 1) * limit
            
            history = list(db[CHAT_HISTORY_COLLECTION].find(
                {'user_id': user_id}
            ).sort('timestamp', -1).skip(skip).limit(limit))
            
            for chat in history:
                chat['_id'] = str(chat['_id'])
                chat['timestamp'] = chat['timestamp'].isoformat()
            
            return format_response(data=history, status=200)
            
        except Exception as e:
            return format_response(error=f"Failed to fetch chat history: {str(e)}", status=400)


# class FileService:
#     def upload_csv(self, file, request):
#         """Upload and process CSV file"""
#         try:
#             if not file or not file.filename:
#                 return format_response(error="No file provided", status=400)
            
#             if not file.filename.endswith('.csv'):
#                 return format_response(error="File must be CSV format", status=400)
            
#             user_data = get_user_from_token(request)
            
#             # Read CSV
#             df = pd.read_csv(file)
            
#             # Validate columns
#             required_columns = list(CSV_COLUMN_MAPPING.keys())
#             missing_columns = [col for col in required_columns if col not in df.columns]
            
#             if missing_columns:
#                 return format_response(
#                     error=f"Missing columns: {', '.join(missing_columns)}",
#                     status=400
#                 )
            
#             # Process rows
#             success_count = 0
#             error_count = 0
#             errors = []
            
#             for index, row in df.iterrows():
#                 try:
#                     # Map CSV columns to database fields
#                     resource_doc = {}
#                     for csv_col, db_field in CSV_COLUMN_MAPPING.items():
#                         resource_doc[db_field] = row[csv_col]
                    
#                     # Convert cost to float
#                     resource_doc['cost'] = float(resource_doc['cost'])
                    
#                     # Add metadata
#                     resource_doc['created_by'] = user_data['email']
#                     resource_doc['created_at'] = datetime.datetime.utcnow()
#                     resource_doc['updated_at'] = datetime.datetime.utcnow()
                    
#                     # Insert resource
#                     db[RESOURCES_COLLECTION].insert_one(resource_doc)
#                     success_count += 1
                    
#                 except Exception as e:
#                     error_count += 1
#                     errors.append(f"Row {index + 1}: {str(e)}")
            
#             return format_response(
#                 data={
#                     'success_count': success_count,
#                     'error_count': error_count,
#                     'errors': errors[:10]  # Limit error messages
#                 },
#                 message=f"CSV processed. {success_count} records added, {error_count} errors.",
#                 status=200
#             )
            
#         except Exception as e:
#             return format_response(error=f"CSV upload failed: {str(e)}", status=500)
    
#     def upload_excel(self, file, request):
#         """Upload and process Excel file"""
#         try:
#             if not file or not file.filename:
#                 return format_response(error="No file provided", status=400)
            
#             if not file.filename.endswith(('.xlsx', '.xls')):
#                 return format_response(error="File must be Excel format", status=400)
            
#             user_data = get_user_from_token(request)
            
#             # Read Excel
#             df = pd.read_excel(file)
            
#             # Validate columns
#             required_columns = list(CSV_COLUMN_MAPPING.keys())
#             missing_columns = [col for col in required_columns if col not in df.columns]
            
#             if missing_columns:
#                 return format_response(
#                     error=f"Missing columns: {', '.join(missing_columns)}",
#                     status=400
#                 )
            
#             # Process rows (same as CSV)
#             success_count = 0
#             error_count = 0
#             errors = []
            
#             for index, row in df.iterrows():
#                 try:
#                     resource_doc = {}
#                     for csv_col, db_field in CSV_COLUMN_MAPPING.items():
#                         resource_doc[db_field] = row[csv_col]
                    
#                     resource_doc['cost'] = float(resource_doc['cost'])
#                     resource_doc['created_by'] = user_data['email']
#                     resource_doc['created_at'] = datetime.datetime.utcnow()
#                     resource_doc['updated_at'] = datetime.datetime.utcnow()
                    
#                     db[RESOURCES_COLLECTION].insert_one(resource_doc)
#                     success_count += 1
                    
#                 except Exception as e:
#                     error_count += 1
#                     errors.append(f"Row {index + 1}: {str(e)}")
            
#             return format_response(
#                 data={
#                     'success_count': success_count,
#                     'error_count': error_count,
#                     'errors': errors[:10]
#                 },
#                 message=f"Excel processed. {success_count} records added, {error_count} errors.",
#                 status=200
#             )
            
#         except Exception as e:
#             return format_response(error=f"Excel upload failed: {str(e)}", status=500)
    
#     def export_csv(self, filters):
#         """Export resources to CSV"""
#         try:
#             # Build query from filters
#             query = {}
#             if 'location' in filters and filters['location']:
#                 query['location'] = filters['location']
#             if 'department' in filters and filters['department']:
#                 query['department'] = filters['department']
            
#             # Get resources
#             resources = list(db[RESOURCES_COLLECTION].find(query))
            
#             if not resources:
#                 return format_response(error="No data found", status=404)
            
#             # Convert to DataFrame
#             df = pd.DataFrame(resources)
            
#             # Remove MongoDB-specific fields
#             df.drop(columns=['_id', 'created_at', 'updated_at', 'created_by'], inplace=True, errors='ignore')
            
#             # Rename columns to match CSV format
#             reverse_mapping = {v: k for k, v in CSV_COLUMN_MAPPING.items()}
#             df.rename(columns=reverse_mapping, inplace=True)
            
#             # Convert to CSV
#             csv_data = df.to_csv(index=False)
            
#             # Create response
#             output = io.BytesIO()
#             output.write(csv_data.encode('utf-8'))
#             output.seek(0)
            
#             return send_file(
#                 output,
#                 mimetype='text/csv',
#                 as_attachment=True,
#                 download_name='resources_export.csv'
#             )
            
#         except Exception as e:
#             return format_response(error=f"CSV export failed: {str(e)}", status=500)
    
#     def export_excel(self, filters):
#         """Export resources to Excel"""
#         try:
#             # Build query from filters
#             query = {}
#             if 'location' in filters and filters['location']:
#                 query['location'] = filters['location']
#             if 'department' in filters and filters['department']:
#                 query['department'] = filters['department']
            
#             # Get resources
#             resources = list(db[RESOURCES_COLLECTION].find(query))
            
#             if not resources:
#                 return format_response(error="No data found", status=404)
            
#             # Convert to DataFrame
#             df = pd.DataFrame(resources)
            
#             # Remove MongoDB-specific fields
#             df.drop(columns=['_id', 'created_at', 'updated_at', 'created_by'], inplace=True, errors='ignore')
            
#             # Rename columns to match CSV format
#             reverse_mapping = {v: k for k, v in CSV_COLUMN_MAPPING.items()}
#             df.rename(columns=reverse_mapping, inplace=True)
            
#             # Create Excel file
#             output = io.BytesIO()
#             with pd.ExcelWriter(output, engine='openpyxl') as writer:
#                 df.to_excel(writer, index=False, sheet_name='Resources')
            
#             output.seek(0)
            
#             return send_file(
#                 output,
#                 mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
#                 as_attachment=True,
#                 download_name='resources_export.xlsx'
#             )
            
#         except Exception as e:
#             return format_response(error=f"Excel export failed: {str(e)}", status=500)

import pandas as pd
import datetime
import re
from flask import send_file
import io

# class FileService:
#     def detect_special_excel_format(self, df):
#         """Detect if this is the special multi-section Excel format"""
#         try:
#             if len(df) < 10:
#                 return False
            
#             first_few_rows = df.head(10).astype(str)
            
#             # Check for department/institution keywords
#             header_keywords = ['DEPARTMENT', 'INSTITUTE', 'TECHNOLOGY', 'ENGINEERING']
#             has_header_info = any(
#                 any(keyword in str(cell).upper() for keyword in header_keywords)
#                 for row in first_few_rows.values
#                 for cell in row if pd.notna(cell)
#             )
            
#             # Check for location sections
#             location_keywords = ['Laboratory', 'Lab', 'Facility', 'Centre', 'Center', 'Computing']
#             has_location_sections = any(
#                 any(keyword in str(cell) for keyword in location_keywords)
#                 for row in df.values
#                 for cell in row if pd.notna(cell) and len(str(cell).strip()) > 0
#             )
            
#             return has_header_info and has_location_sections
#         except Exception as e:
#             print(f"Error detecting special format: {e}")
#             return False

#     def parse_special_excel_format(self, df):
#         """Enhanced parsing for special multi-section Excel format"""
#         resources = []
#         current_section = None
#         current_section_data = []
#         table_headers = None
#         processing_table = False
        
#         try:
#             for index, row in df.iterrows():
#                 row_values = [str(cell).strip() if pd.notna(cell) else '' for cell in row]
#                 non_empty_values = [val for val in row_values if val and val != 'nan' and val != '']
                
#                 # Skip completely empty rows
#                 if not non_empty_values:
#                     continue
                
#                 # Skip header rows (first 5 rows)
#                 if index < 5:
#                     continue
                
#                 # Check if this is a section header (product category)
#                 if self.is_section_header(non_empty_values):
#                     # Process previous section if exists
#                     if current_section and current_section_data:
#                         section_resources = self.process_section_data(
#                             current_section_data, current_section, table_headers
#                         )
#                         resources.extend(section_resources)
                    
#                     # Start new section
#                     current_section = {
#                         'name': non_empty_values[0],
#                         'product_category': self.extract_product_category(non_empty_values[0])
#                     }
#                     current_section_data = []
#                     table_headers = None
#                     processing_table = False
#                     print(f"New section: {current_section['name']}")
#                     continue
                
#                 # Check if this is a table header row
#                 if self.is_table_header(row_values):
#                     table_headers = [val.strip() for val in row_values if val and val != 'nan']
#                     processing_table = True
#                     print(f"Table headers found: {table_headers}")
#                     continue
                
#                 # Check if this is a data row
#                 if processing_table and table_headers and self.is_data_row(non_empty_values, table_headers):
#                     row_dict = self.create_row_dict(row_values, table_headers)
#                     if row_dict:
#                         row_dict['Section_Location'] = current_section['name'] if current_section else ''
#                         row_dict['Product_Category'] = current_section['product_category'] if current_section else ''
#                         current_section_data.append(row_dict)
#                         print(f"Added data row: SL No {row_dict.get('Sl. No', 'N/A')}")
#                     continue
                
#                 # Check for summary rows or section ends
#                 if self.is_summary_row(non_empty_values):
#                     processing_table = False
#                     continue
            
#             # Process the last section
#             if current_section and current_section_data:
#                 section_resources = self.process_section_data(
#                     current_section_data, current_section, table_headers
#                 )
#                 resources.extend(section_resources)
            
#             print(f"Total resources parsed: {len(resources)}")
#             return resources
            
#         except Exception as e:
#             print(f"Error parsing special Excel format: {e}")
#             return []
# # Add to your FileService class in services.py

#     def clean_cost_value(self, cost_value):
#         """Clean and validate cost values"""
#         try:
#             if not cost_value or cost_value in ['---', '', 'N/A', 'NA', '-', 'NULL']:
#                 return 0.0
            
#             # Remove currency symbols and whitespace
#             cost_clean = re.sub(r'[₹,$\s]', '', str(cost_value))
            
#             # Handle comma-separated thousands
#             cost_clean = cost_clean.replace(',', '')
            
#             return float(cost_clean)
#         except (ValueError, TypeError):
#             return 0.0

#     def upload_excel(self, file, request):
#         """Enhanced Excel upload with better error handling"""
#         try:
#             if not file or not file.filename:
#                 return format_response(error="No file provided", status=400)
            
#             if not file.filename.endswith(('.xlsx', '.xls')):
#                 return format_response(error="File must be Excel format", status=400)

#             user_data = get_user_from_token(request)
            
#             # Read Excel file
#             df = pd.read_excel(file)
            
#             # Detect if this is the special format
#             is_special_format = self.detect_special_excel_format(df)
            
#             if is_special_format:
#                 print("Detected special multi-section Excel format")
#                 resources_data = self.parse_special_excel_format(df)
                
#                 # Process the parsed resources with enhanced error handling
#                 success_count = 0
#                 error_count = 0
#                 errors = []
                
#                 for resource_data in resources_data:
#                     try:
#                         # Enhanced cost cleaning
#                         cost_value = self.clean_cost_value(resource_data.get('cost', '0'))
                        
#                         # Create resource document with enhanced fields
#                         resource_doc = {
#                             'sl_no': str(resource_data.get('sl_no', '')),
#                             'description': resource_data.get('description', ''),
#                             'service_tag': resource_data.get('service_tag', f"ST-{resource_data.get('sl_no', 'unknown')}"),
#                             'identification_number': resource_data.get('identification_number', ''),
#                             'procurement_date': resource_data.get('procurement_date', '2024-01-01'),
#                             'cost': cost_value,
#                             'location': resource_data.get('location', ''),
#                             'section_location': resource_data.get('section_location', ''),
#                             'product_category': resource_data.get('product_category', 'General Equipment'),
#                             'department': resource_data.get('department', 'Electronics and Instrumentation Engineering'),
#                             'created_by': user_data['email'],
#                             'created_at': datetime.datetime.utcnow(),
#                             'updated_at': datetime.datetime.utcnow()
#                         }
                        
#                         # Insert resource
#                         db[RESOURCES_COLLECTION].insert_one(resource_doc)
#                         success_count += 1
                        
#                     except Exception as e:
#                         error_count += 1
#                         errors.append(f"Resource {resource_data.get('sl_no', 'unknown')}: {str(e)}")
                
#                 return format_response(
#                     data={
#                         'success_count': success_count,
#                         'error_count': error_count,
#                         'errors': errors[:10],
#                         'format_type': 'special_multi_section'
#                     },
#                     message=f"Special format Excel processed. {success_count} records added, {error_count} errors.",
#                     status=200
#                 )
            
#             else:
#                 # Use standard processing for normal Excel files
#                 return self.upload_excel_standard(df, user_data)
                
#         except Exception as e:
#             return format_response(error=f"Excel upload failed: {str(e)}", status=500)

#     def is_section_header(self, non_empty_values):
#         """Check if row is a section header"""
#         if len(non_empty_values) != 1:
#             return False
        
#         value = non_empty_values[0]
#         section_keywords = [
#             'Laboratory', 'Lab', 'Facility', 'Centre', 'Center', 'Computing',
#             'Workshop', 'Department', 'Office', 'Room', 'Hall', 'Block'
#         ]
        
#         return any(keyword in value for keyword in section_keywords) and 'Sl. No' not in value

#     def is_table_header(self, row_values):
#         """Check if row contains table headers"""
#         header_indicators = ['Sl. No', 'Sl.No', 'SlNo', 'Serial', 'Description', 'Desc']
#         return any(indicator in str(val) for val in row_values for indicator in header_indicators)

#     def is_data_row(self, non_empty_values, table_headers):
#         """Check if row is a data row"""
#         if not non_empty_values or not table_headers:
#             return False
        
#         first_value = non_empty_values[0].strip()
        
#         # Check if first value looks like a serial number
#         try:
#             int(first_value)
#             return True
#         except ValueError:
#             # Handle cases where SL No might have text like "1a", "1b"
#             if re.match(r'^\d+[a-zA-Z]?$', first_value):
#                 return True
#             return False

#     def is_summary_row(self, non_empty_values):
#         """Check if row is a summary/total row"""
#         if len(non_empty_values) == 1:
#             value = non_empty_values[0]
#             if value.isdigit() and len(value) <= 3:  # Likely a count summary
#                 return True
#         return False

#     def extract_product_category(self, section_name):
#         """Extract product category from section name"""
#         # Map section types to categories
#         category_mapping = {
#             'Computer': 'Computing Equipment',
#             'Laboratory': 'Lab Equipment', 
#             'Workshop': 'Workshop Tools',
#             'Facility': 'Infrastructure',
#             'Office': 'Office Equipment'
#         }
        
#         for keyword, category in category_mapping.items():
#             if keyword.lower() in section_name.lower():
#                 return category
        
#         return 'General Equipment'

#     def create_row_dict(self, row_values, table_headers):
#         """Create dictionary from row values and headers"""
#         try:
#             row_dict = {}
#             for i, header in enumerate(table_headers):
#                 if i < len(row_values):
#                     value = row_values[i].strip() if row_values[i] else ''
#                     row_dict[header] = value
            
#             return row_dict
#         except Exception as e:
#             print(f"Error creating row dict: {e}")
#             return None

#     def process_section_data(self, section_data, section_info, headers):
#         """Process data from a single section with enhanced field mapping"""
#         resources = []
        
#         try:
#             for row_data in section_data:
#                 resource = {}
                
#                 # Enhanced field mapping with multiple possible column names
#                 field_mappings = {
#                     'sl_no': ['Sl. No', 'Sl.No', 'SlNo', 'Sl No', 'Serial No', 'S.No'],
#                     'description': ['Description', 'Desctiption', 'Desc', 'Item Description', 'Item'],
#                     'service_tag': ['Service Tag', 'ServiceTag', 'Service No', 'Asset Tag'],
#                     'identification_number': ['Identification No', 'Identification Number', 'ID No', 'Asset ID', 'Equipment ID'],
#                     'procurement_date': ['Procurement Date', 'ProcurementDate', 'Date', 'Purchase Date'],
#                     'cost': ['Cost', 'Price', 'Amount', 'Value'],
#                     'location': ['Location', 'Place', 'Room', 'Position']
#                 }
                
#                 # Map fields using flexible matching
#                 for field, possible_keys in field_mappings.items():
#                     resource[field] = self.get_value_by_keys(row_data, possible_keys)
                
#                 # Handle cost field with '---' values
#                 cost_value = resource['cost']
#                 if cost_value in ['---', '', 'N/A', 'NA', '-']:
#                     resource['cost'] = '0'
#                 else:
#                     # Clean cost value (remove currency symbols, commas)
#                     cost_clean = re.sub(r'[₹,\s]', '', str(cost_value))
#                     try:
#                         float(cost_clean)
#                         resource['cost'] = cost_clean
#                     except ValueError:
#                         resource['cost'] = '0'
                
#                 # Set section-based fields
#                 resource['section_location'] = section_info['name']
#                 resource['product_category'] = section_info['product_category']
                
#                 # Use table location if available, otherwise use section location
#                 table_location = resource['location']
#                 if not table_location or table_location.strip() == '':
#                     resource['location'] = section_info['name']
                
#                 # Set department
#                 resource['department'] = self.extract_department_from_section(section_info['name'])
                
#                 # Validate required fields
#                 if (resource['sl_no'] and resource['description'] and 
#                     resource['identification_number']):
                    
#                     # Set default values for missing fields
#                     if not resource['service_tag']:
#                         resource['service_tag'] = f"ST-{resource['sl_no']}"
                    
#                     if not resource['procurement_date']:
#                         resource['procurement_date'] = '2024-01-01'
                    
#                     resources.append(resource)
#                 else:
#                     print(f"Skipping incomplete record: {resource}")
                
#         except Exception as e:
#             print(f"Error processing section data: {e}")
        
#         return resources

#     def extract_department_from_section(self, section_name):
#         """Extract department from section name"""
#         if 'Computer' in section_name or 'Computing' in section_name:
#             return 'Computer Science and Engineering'
#         elif 'Electronics' in section_name or 'Instrumentation' in section_name:
#             return 'Electronics and Instrumentation Engineering'
#         elif 'Mechanical' in section_name:
#             return 'Mechanical Engineering'
#         elif 'Civil' in section_name:
#             return 'Civil Engineering'
#         else:
#             return 'Electronics and Instrumentation Engineering'

#     def get_value_by_keys(self, data_dict, possible_keys):
#         """Get value from dictionary using multiple possible keys"""
#         for key in possible_keys:
#             if key in data_dict and data_dict[key]:
#                 return data_dict[key].strip()
#         return ''

#     def upload_excel(self, file, request):
#         """Enhanced Excel upload with improved special format processing"""
#         try:
#             if not file or not file.filename:
#                 return format_response(error="No file provided", status=400)
            
#             if not file.filename.endswith(('.xlsx', '.xls')):
#                 return format_response(error="File must be Excel format", status=400)

#             user_data = get_user_from_token(request)
            
#             # Read Excel file
#             df = pd.read_excel(file)
#             print(f"Excel file loaded with {len(df)} rows")
            
#             # Detect if this is the special format
#             is_special_format = self.detect_special_excel_format(df)
            
#             if is_special_format:
#                 print("Detected special multi-section Excel format")
#                 resources_data = self.parse_special_excel_format(df)
                
#                 # Process the parsed resources
#                 success_count = 0
#                 error_count = 0
#                 errors = []
                
#                 for resource_data in resources_data:
#                     try:
#                         # Create resource document
#                         resource_doc = {
#                             'sl_no': str(resource_data['sl_no']),
#                             'description': resource_data['description'],
#                             'service_tag': resource_data['service_tag'],
#                             'identification_number': resource_data['identification_number'],
#                             'procurement_date': resource_data['procurement_date'],
#                             'cost': float(resource_data['cost']),
#                             'location': resource_data['location'],
#                             'section_location': resource_data.get('section_location', ''),
#                             'product_category': resource_data.get('product_category', 'General Equipment'),
#                             'department': resource_data['department'],
#                             'created_by': user_data['email'],
#                             'created_at': datetime.datetime.utcnow(),
#                             'updated_at': datetime.datetime.utcnow()
#                         }
                        
#                         # Insert resource
#                         db[RESOURCES_COLLECTION].insert_one(resource_doc)
#                         success_count += 1
                        
#                     except Exception as e:
#                         error_count += 1
#                         errors.append(f"Resource {resource_data.get('sl_no', 'unknown')}: {str(e)}")
#                         print(f"Error processing resource: {e}")
                
#                 return format_response(
#                     data={
#                         'success_count': success_count,
#                         'error_count': error_count,
#                         'errors': errors[:10],
#                         'format_type': 'special_multi_section'
#                     },
#                     message=f"Special format Excel processed. {success_count} records added, {error_count} errors.",
#                     status=200
#                 )
            
#             else:
#                 # Use standard processing for normal Excel files
#                 return self.upload_excel_standard(df, user_data)
                
#         except Exception as e:
#             print(f"Excel upload error: {e}")
#             return format_response(error=f"Excel upload failed: {str(e)}", status=500)

#     def upload_excel_standard(self, df, user_data):
#         """Standard Excel processing for normal tabular format"""
#         try:
#             # Validate columns for standard format
#             required_columns = list(CSV_COLUMN_MAPPING.keys())
#             missing_columns = [col for col in required_columns if col not in df.columns]
            
#             if missing_columns:
#                 return format_response(
#                     error=f"Missing columns: {', '.join(missing_columns)}",
#                     status=400
#                 )
            
#             # Process rows (same as original)
#             success_count = 0
#             error_count = 0
#             errors = []
            
#             for index, row in df.iterrows():
#                 try:
#                     resource_doc = {}
#                     for csv_col, db_field in CSV_COLUMN_MAPPING.items():
#                         resource_doc[db_field] = row[csv_col]
                    
#                     resource_doc['cost'] = float(resource_doc['cost'])
#                     resource_doc['created_by'] = user_data['email']
#                     resource_doc['created_at'] = datetime.datetime.utcnow()
#                     resource_doc['updated_at'] = datetime.datetime.utcnow()
                    
#                     db[RESOURCES_COLLECTION].insert_one(resource_doc)
#                     success_count += 1
                    
#                 except Exception as e:
#                     error_count += 1
#                     errors.append(f"Row {index + 1}: {str(e)}")
            
#             return format_response(
#                 data={
#                     'success_count': success_count,
#                     'error_count': error_count,
#                     'errors': errors[:10],
#                     'format_type': 'standard_tabular'
#                 },
#                 message=f"Standard Excel processed. {success_count} records added, {error_count} errors.",
#                 status=200
#             )
            
#         except Exception as e:
#             return format_response(error=f"Standard Excel processing failed: {str(e)}", status=500)

#     def upload_csv(self, file, request):
#         """CSV upload (unchanged - for standard format)"""
#         try:
#             if not file or not file.filename:
#                 return format_response(error="No file provided", status=400)
            
#             if not file.filename.endswith('.csv'):
#                 return format_response(error="File must be CSV format", status=400)

#             user_data = get_user_from_token(request)
            
#             # Read CSV
#             df = pd.read_csv(file)
            
#             # Validate columns
#             required_columns = list(CSV_COLUMN_MAPPING.keys())
#             missing_columns = [col for col in required_columns if col not in df.columns]
            
#             if missing_columns:
#                 return format_response(
#                     error=f"Missing columns: {', '.join(missing_columns)}",
#                     status=400
#                 )
            
#             # Process rows
#             success_count = 0
#             error_count = 0
#             errors = []
            
#             for index, row in df.iterrows():
#                 try:
#                     # Map CSV columns to database fields
#                     resource_doc = {}
#                     for csv_col, db_field in CSV_COLUMN_MAPPING.items():
#                         resource_doc[db_field] = row[csv_col]
                    
#                     # Convert cost to float
#                     resource_doc['cost'] = float(resource_doc['cost'])
                    
#                     # Add metadata
#                     resource_doc['created_by'] = user_data['email']
#                     resource_doc['created_at'] = datetime.datetime.utcnow()
#                     resource_doc['updated_at'] = datetime.datetime.utcnow()
                    
#                     # Insert resource
#                     db[RESOURCES_COLLECTION].insert_one(resource_doc)
#                     success_count += 1
                    
#                 except Exception as e:
#                     error_count += 1
#                     errors.append(f"Row {index + 1}: {str(e)}")
            
#             return format_response(
#                 data={
#                     'success_count': success_count,
#                     'error_count': error_count,
#                     'errors': errors[:10]
#                 },
#                 message=f"CSV processed. {success_count} records added, {error_count} errors.",
#                 status=200
#             )
            
#         except Exception as e:
#             return format_response(error=f"CSV upload failed: {str(e)}", status=500)

#     def export_csv(self, filters):
#         """Export resources to CSV (unchanged)"""
#         try:
#             # Build query from filters
#             query = {}
#             if 'location' in filters and filters['location']:
#                 query['location'] = filters['location']
#             if 'department' in filters and filters['department']:
#                 query['department'] = filters['department']
            
#             # Get resources
#             resources = list(db[RESOURCES_COLLECTION].find(query))
#             if not resources:
#                 return format_response(error="No data found", status=404)
            
#             # Convert to DataFrame
#             df = pd.DataFrame(resources)
            
#             # Remove MongoDB-specific fields
#             df.drop(columns=['_id', 'created_at', 'updated_at', 'created_by'], inplace=True, errors='ignore')
            
#             # Rename columns to match CSV format
#             reverse_mapping = {v: k for k, v in CSV_COLUMN_MAPPING.items()}
#             df.rename(columns=reverse_mapping, inplace=True)
            
#             # Convert to CSV
#             csv_data = df.to_csv(index=False)
            
#             # Create response
#             output = io.BytesIO()
#             output.write(csv_data.encode('utf-8'))
#             output.seek(0)
            
#             return send_file(
#                 output,
#                 mimetype='text/csv',
#                 as_attachment=True,
#                 download_name='resources_export.csv'
#             )
            
#         except Exception as e:
#             return format_response(error=f"CSV export failed: {str(e)}", status=500)

#     def export_excel(self, filters):
#         """Export resources to Excel (unchanged)"""
#         try:
#             # Build query from filters
#             query = {}
#             if 'location' in filters and filters['location']:
#                 query['location'] = filters['location']
#             if 'department' in filters and filters['department']:
#                 query['department'] = filters['department']
            
#             # Get resources
#             resources = list(db[RESOURCES_COLLECTION].find(query))
#             if not resources:
#                 return format_response(error="No data found", status=404)
            
#             # Convert to DataFrame
#             df = pd.DataFrame(resources)
            
#             # Remove MongoDB-specific fields
#             df.drop(columns=['_id', 'created_at', 'updated_at', 'created_by'], inplace=True, errors='ignore')
            
#             # Rename columns to match CSV format
#             reverse_mapping = {v: k for k, v in CSV_COLUMN_MAPPING.items()}
#             df.rename(columns=reverse_mapping, inplace=True)
            
#             # Create Excel file
#             output = io.BytesIO()
#             with pd.ExcelWriter(output, engine='openpyxl') as writer:
#                 df.to_excel(writer, index=False, sheet_name='Resources')
#             output.seek(0)
            
#             return send_file(
#                 output,
#                 mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
#                 as_attachment=True,
#                 download_name='resources_export.xlsx'
#             )
            
#         except Exception as e:
#             return format_response(error=f"Excel export failed: {str(e)}", status=500)

import pandas as pd
import datetime
import io
from flask import send_file
# Assuming other necessary imports like db, format_response, get_user_from_token, etc., are present

class FileService:
    def __init__(self):
        # Standard required columns
        self.required_columns = [
            'SL No', 'Description', 'Service Tag', 'Identification Number', 
            'Procurement Date', 'Cost', 'Location', 'Department'
        ]
    
    def is_standard_format(self, df):
        """Check if Excel file has standard format"""
        try:
            if len(df.columns) < 8: return False
            
            first_row = df.iloc[0] if len(df) > 0 else pd.Series()
            header_match_count = 0
            
            for required_col in self.required_columns:
                if any(required_col.lower() in str(col).lower() for col in df.columns):
                    header_match_count += 1
                elif any(required_col.lower() in str(cell).lower() for cell in first_row.values):
                    header_match_count += 1
            
            return header_match_count >= 6
        except Exception as e:
            print(f"Error checking standard format: {e}")
            return False
    
    def clean_complex_excel(self, df, parent_department_from_user):
        """Cleans complex Excel, preserving file's department and adding parent department."""
        try:
            print("Applying complex Excel cleaning logic...")
            data_list = []
            current_department = None
            last_description = None
            last_location = None
            sl_no_counter = 1
            
            for index, row in df.iterrows():
                if pd.isna(row).all(): continue
                if not pd.isna(row[0]) and pd.isna(row[1:]).all():
                    current_department = str(row[0]).strip()
                    continue
                if str(row[0]).strip() == 'Sl. No': continue
                
                if not pd.isna(row[0]) and str(row[0]).strip().replace('.', '').isdigit():
                    description = str(row[1]).strip() if not pd.isna(row[1]) else (last_description or "")
                    service_tag = str(row[2]).strip() if not pd.isna(row[2]) else ""
                    identification_no = str(row[3]).strip() if not pd.isna(row[3]) else ""
                    
                    procurement_date = ""
                    if not pd.isna(row[4]):
                        try:
                            procurement_date = pd.to_datetime(row[4]).strftime('%Y-%m-%d')
                        except:
                            procurement_date = str(row[4])
                    
                    cost = 0.0
                    if not pd.isna(row[5]):
                        try:
                            cost_str = str(row[5]).replace(',', '').replace('₹', '').strip()
                            cost = float(cost_str) if cost_str else 0.0
                        except:
                            cost = 0.0
                    
                    location = str(row[6]).strip() if not pd.isna(row[6]) else (last_location or "")
                    
                    if not pd.isna(row[1]) and str(row[1]).strip(): last_description = str(row[1]).strip()
                    if not pd.isna(row[6]) and str(row[6]).strip(): last_location = str(row[6]).strip()
                    
                    cleaned_entry = {
                        'SL No': sl_no_counter,
                        'Description': description or f"Item {sl_no_counter}",
                        'Service Tag': service_tag or f"ST-{sl_no_counter}",
                        'Identification Number': identification_no or f"ID-{sl_no_counter}",
                        'Procurement Date': procurement_date or "2024-01-01",
                        'Cost': cost,
                        'Location': location or "General Location",
                        'Department': current_department or "Unspecified",  # From file
                        'Parent Department': parent_department_from_user  # From user
                    }
                    data_list.append(cleaned_entry)
                    sl_no_counter += 1
            
            print(f"Cleaned {len(data_list)} records from complex Excel")
            return pd.DataFrame(data_list)
        except Exception as e:
            print(f"Error in complex Excel cleaning: {e}")
            return pd.DataFrame()
    
    def upload_excel(self, file, request, parent_department):
        """Handle Excel upload, check format, and assign parent department."""
        try:
            if not file or not file.filename.endswith(('.xlsx', '.xls')):
                return format_response(error="File must be Excel format", status=400)

            user_data = get_user_from_token(request)
            if not user_data:
                return format_response(error="Authentication required", status=401)
            
            df = pd.read_excel(file, header=None)
            
            if self.is_standard_format(df):
                print("Detected standard format Excel")
                df_with_header = pd.read_excel(file)
                return self.process_standard_excel(df_with_header, user_data, parent_department)
            else:
                print("Detected complex format Excel - applying cleaner logic")
                cleaned_df = self.clean_complex_excel(df, parent_department)
                if cleaned_df.empty:
                    return format_response(error="Failed to clean Excel data", status=400)
                return self.process_cleaned_excel(cleaned_df, user_data)
        except Exception as e:
            print(f"Excel upload error: {e}")
            return format_response(error=f"Excel upload failed: {str(e)}", status=500)
    
    def process_standard_excel(self, df, user_data, parent_department_from_user):
        """Process standard format Excel and assign parent department."""
        success_count, error_count, errors = 0, 0, []
        for index, row in df.iterrows():
            try:
                resource_doc = {
                    'sl_no': str(row.get('SL No', index + 1)),
                    'description': str(row.get('Description', f'Item {index + 1}')),
                    'service_tag': str(row.get('Service Tag', f'ST-{index + 1}')),
                    'identification_number': str(row.get('Identification Number', f'ID-{index + 1}')),
                    'procurement_date': str(row.get('Procurement Date', '2024-01-01')),
                    'cost': float(str(row.get('Cost', 0)).replace(',', '').replace('₹', '') or 0),
                    'location': str(row.get('Location', 'General Location')),
                    'department': str(row.get('Department', 'Unspecified')),  # From file
                    'parent_department': parent_department_from_user,  # From user
                    'created_by': user_data['email'],
                    'created_at': datetime.datetime.utcnow(),
                    'updated_at': datetime.datetime.utcnow()
                }
                db[RESOURCES_COLLECTION].insert_one(resource_doc)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Row {index + 2}: {str(e)}")
        
        return format_response(data={
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:10],
            'format_type': 'standard'
        }, status=200)

    def process_cleaned_excel(self, cleaned_df, user_data):
        """Process DataFrame from cleaned complex Excel."""
        success_count, error_count, errors = 0, 0, []
        for index, row in cleaned_df.iterrows():
            try:
                resource_doc = {
                    'sl_no': str(row['SL No']),
                    'description': str(row['Description']),
                    'service_tag': str(row['Service Tag']),
                    'identification_number': str(row['Identification Number']),
                    'procurement_date': str(row['Procurement Date']),
                    'cost': float(row['Cost'] or 0.0),
                    'location': str(row['Location']),
                    'department': str(row['Department']),  # From file (via cleaning)
                    'parent_department': str(row['Parent Department']),  # From user (via cleaning)
                    'created_by': user_data['email'],
                    'created_at': datetime.datetime.utcnow(),
                    'updated_at': datetime.datetime.utcnow()
                }
                db[RESOURCES_COLLECTION].insert_one(resource_doc)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Row {index + 1}: {str(e)}")
                
        return format_response(data={
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:10],
            'format_type': 'cleaned_complex'
        }, status=200)

    def upload_csv(self, file, request, parent_department_from_user):
        """Process CSV file, preserving file's department and adding parent department."""
        try:
            if not file.filename.endswith('.csv'):
                return format_response(error="File must be CSV format", status=400)
            
            user_data = get_user_from_token(request)
            if not user_data:
                return format_response(error="Authentication required", status=401)
            
            df = pd.read_csv(file)
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                return format_response(error=f"Missing columns: {', '.join(missing_columns)}", status=400)

            success_count, error_count, errors = 0, 0, []
            for index, row in df.iterrows():
                try:
                    resource_doc = {
                        'sl_no': str(row['SL No']),
                        'description': str(row['Description']),
                        'service_tag': str(row['Service Tag']),
                        'identification_number': str(row['Identification Number']),
                        'procurement_date': str(row['Procurement Date']),
                        'cost': float(str(row['Cost']).replace(',', '').replace('₹', '') or 0),
                        'location': str(row['Location']),
                        'department': str(row.get('Department', 'Unspecified')),  # From file
                        'parent_department': parent_department_from_user,  # From user
                        'created_by': user_data['email'],
                        'created_at': datetime.datetime.utcnow(),
                        'updated_at': datetime.datetime.utcnow()
                    }
                    db[RESOURCES_COLLECTION].insert_one(resource_doc)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return format_response(data={
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors[:10]
            }, status=200)
        except Exception as e:
            return format_response(error=f"CSV upload failed: {str(e)}", status=500)
    

    def export_csv(self, filters):
        """Export resources to CSV"""
        try:
            # Build query from filters
            query = {}
            if 'location' in filters and filters['location']:
                query['location'] = {'$regex': filters['location'], '$options': 'i'}
            if 'department' in filters and filters['department']:
                query['department'] = {'$regex': filters['department'], '$options': 'i'}
            
            # Get resources
            resources = list(db[RESOURCES_COLLECTION].find(query))
            if not resources:
                return format_response(error="No data found", status=404)
            
            # Convert to DataFrame
            df = pd.DataFrame(resources)
            
            # Remove MongoDB-specific fields
            df.drop(columns=['_id', 'created_at', 'updated_at', 'created_by'], inplace=True, errors='ignore')
            
            # Rename columns to match CSV format
            column_mapping = {
                'sl_no': 'SL No',
                'description': 'Description',
                'service_tag': 'Service Tag',
                'identification_number': 'Identification Number',
                'procurement_date': 'Procurement Date',
                'cost': 'Cost',
                'location': 'Location',
                'department': 'Department',
                'parent_department': 'Parent Department'
            }
            df.rename(columns=column_mapping, inplace=True)
            
            # Convert to CSV
            csv_data = df.to_csv(index=False)
            
            # Create response
            output = io.BytesIO()
            output.write(csv_data.encode('utf-8'))
            output.seek(0)
            
            return send_file(
                output,
                mimetype='text/csv',
                as_attachment=True,
                download_name='resources_export.csv'
            )
            
        except Exception as e:
            return format_response(error=f"CSV export failed: {str(e)}", status=500)
    
    def export_excel(self, filters):
        """Export resources to Excel"""
        try:
            # Build query from filters
            query = {}
            if 'location' in filters and filters['location']:
                query['location'] = {'$regex': filters['location'], '$options': 'i'}
            if 'department' in filters and filters['department']:
                query['department'] = {'$regex': filters['department'], '$options': 'i'}
            
            # Get resources
            resources = list(db[RESOURCES_COLLECTION].find(query))
            if not resources:
                return format_response(error="No data found", status=404)
            
            # Convert to DataFrame
            df = pd.DataFrame(resources)
            
            # Remove MongoDB-specific fields
            df.drop(columns=['_id', 'created_at', 'updated_at', 'created_by'], inplace=True, errors='ignore')
            
            # Rename columns to match Excel format
            column_mapping = {
                'sl_no': 'SL No',
                'description': 'Description',
                'service_tag': 'Service Tag',
                'identification_number': 'Identification Number',
                'procurement_date': 'Procurement Date',
                'cost': 'Cost',
                'location': 'Location',
                'department': 'Department',
                'parent_department': 'Parent Department'
            }
            df.rename(columns=column_mapping, inplace=True)
            
            # Create Excel file
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Resources')
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='resources_export.xlsx'
            )
            
        except Exception as e:
            return format_response(error=f"Excel export failed: {str(e)}", status=500)