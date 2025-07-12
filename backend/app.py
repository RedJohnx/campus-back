
from flask import Flask, request, jsonify, session, send_file, make_response
from flask_cors import CORS
import traceback
import datetime
import uuid

# Import everything from our modules
from config import (
    FLASK_SECRET_KEY, ADMIN_ROLE, VIEWER_ROLE, db,
    USERS_COLLECTION, RESOURCES_COLLECTION, SESSIONS_COLLECTION, CHAT_HISTORY_COLLECTION,
    USER_STATUS_PENDING, USER_STATUS_APPROVED, USER_STATUS_REJECTED,
    JWT_SECRET
)
from services import AuthService, ResourceService, AIService, FileService
from utils import login_required, admin_required, validate_request_data, format_response
from reports import ReportService


app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Enhanced CORS configuration
CORS(app, 
     supports_credentials=True, 
     origins=["*"],  # Allow all origins for now
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"])

# Add OPTIONS handler for all routes
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

# Initialize services
auth_service = AuthService()
resource_service = ResourceService()
ai_service = AIService()
file_service = FileService()

# Error handler
@app.errorhandler(Exception)
def handle_error(e):
    app.logger.error(f"Unhandled exception: {str(e)}")
    app.logger.error(traceback.format_exc())
    return format_response(error="Internal server error", status=500)

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return format_response(message="Backend is running", status=200)

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        validation_error = validate_request_data(data, ['email', 'password', 'role'])
        if validation_error:
            return validation_error
        
        return auth_service.register_user(data)
    except Exception as e:
        app.logger.error(f"Registration error: {str(e)}")
        return format_response(error="Registration failed", status=400)

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        validation_error = validate_request_data(data, ['idToken'])
        if validation_error:
            return validation_error
        
        return auth_service.login_user(data)
    except Exception as e:
        app.logger.error(f"Login error: {str(e)}")
        return format_response(error="Login failed", status=401)

@app.route('/api/auth/verify-admin', methods=['GET'])
def verify_admin():
    try:
        token = request.args.get('token')
        if not token:
            return format_response(error="Verification token required", status=400)
        
        return auth_service.verify_admin(token)
    except Exception as e:
        app.logger.error(f"Admin verification error: {str(e)}")
        return format_response(error="Admin verification failed", status=400)

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    try:
        return auth_service.logout_user(request)
    except Exception as e:
        app.logger.error(f"Logout error: {str(e)}")
        return format_response(error="Logout failed", status=400)

@app.route('/api/auth/profile', methods=['GET'])
@login_required
def get_profile():
    try:
        return auth_service.get_user_profile(request)
    except Exception as e:
        app.logger.error(f"Profile fetch error: {str(e)}")
        return format_response(error="Failed to fetch profile", status=400)

# ==================== RESOURCE ROUTES ====================
import jwt
from flask import request

def get_user_from_token(request):
    """Extract user data from JWT token"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        return {
            'email': payload.get('email'),
            'role': payload.get('role', 'user'),
            'uid': payload.get('uid'),
        }
        
    except Exception as e:
        print(f"Token validation error: {e}")
        return None

@app.route('/api/resources', methods=['GET'])
@login_required
def get_resources():
    try:
        filters = request.args.to_dict()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        return resource_service.get_resources(filters, page, limit)
    except Exception as e:
        app.logger.error(f"Get resources error: {str(e)}")
        return format_response(error="Failed to fetch resources", status=400)

@app.route('/api/resources', methods=['POST'])
@login_required
@admin_required
def create_resource():
    try:
        data = request.get_json()
        return resource_service.create_resource(data, request)
    except Exception as e:
        app.logger.error(f"Create resource error: {str(e)}")
        return format_response(error="Failed to create resource", status=400)

@app.route('/api/resources/<resource_id>', methods=['GET'])
@login_required
def get_resource(resource_id):
    try:
        return resource_service.get_resource(resource_id)
    except Exception as e:
        app.logger.error(f"Get resource error: {str(e)}")
        return format_response(error="Failed to fetch resource", status=400)

@app.route('/api/resources/<resource_id>', methods=['PUT'])
@login_required
@admin_required
def update_resource(resource_id):
    try:
        data = request.get_json()
        return resource_service.update_resource(resource_id, data, request)
    except Exception as e:
        app.logger.error(f"Update resource error: {str(e)}")
        return format_response(error="Failed to update resource", status=400)

@app.route('/api/resources/<resource_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_resource(resource_id):
    try:
        return resource_service.delete_resource(resource_id)
    except Exception as e:
        app.logger.error(f"Delete resource error: {str(e)}")
        return format_response(error="Failed to delete resource", status=400)

@app.route('/api/resources/search', methods=['GET'])
@login_required
def search_resources():
    try:
        query = request.args.get('q', '')
        filters = request.args.to_dict()
        return resource_service.search_resources(query, filters)
    except Exception as e:
        app.logger.error(f"Search resources error: {str(e)}")
        return format_response(error="Search failed", status=400)

# ==================== NEW FILTER ENDPOINTS ====================

@app.route('/api/filter-options', methods=['GET'])
@login_required
def get_filter_options():
    """Get all filter options for enhanced filtering"""
    try:
        return resource_service.get_filter_options()
    except Exception as e:
        app.logger.error(f"Get filter options error: {str(e)}")
        return format_response(error="Failed to fetch filter options", status=400)



# ==================== NEW/UPDATED FILTER ENDPOINTS ====================

@app.route('/api/departments', methods=['GET'])
@login_required
def get_departments():
    """Get unique departments"""
    return resource_service.get_unique_values('department')

@app.route('/api/locations', methods=['GET'])
@login_required
def get_locations():
    """Get unique locations"""
    return resource_service.get_unique_values('location')

# Add this new endpoint
@app.route('/api/parent-departments', methods=['GET'])
@login_required
def get_parent_departments():
    """Get unique parent departments"""
    return resource_service.get_unique_values('parent_department')


@app.route('/api/product-categories', methods=['GET'])
@login_required
def get_product_categories():
    """Get unique product categories"""
    try:
        return resource_service.get_unique_values('product_category')
    except Exception as e:
        app.logger.error(f"Get product categories error: {str(e)}")
        return format_response(error="Failed to fetch product categories", status=400)
# in app.py

# ==================== STATISTICS ENDPOINT (MODIFIED) ====================
from flask import Flask, jsonify
import pymongo
from datetime import datetime
import math

RESOURCES_COLLECTION = 'resources'

# Assume MongoDB client is initialized elsewhere
client = pymongo.MongoClient("mongodb+srv://kamalkarteek1:rvZSeyVHhgOd2fbE@gbh.iliw2.mongodb.net/")
db = client["campus_assets"]

# In app.py

from datetime import datetime, timezone # Make sure timezone is imported
from flask import jsonify

# In app.py

def format_response(data=None, message=None, status=None, error=None):
    """
    Formats a standard JSON response.
    Uses the modern, timezone-aware method for UTC timestamp.
    """
    # This line will now work because of the 'from datetime import datetime' import
    response = {"timestamp": datetime.now(timezone.utc).isoformat()}

    if data is not None:
        response["data"] = data
    if message is not None:
        response["message"] = message
    if status is not None:
        response["status"] = status
    if error is not None:
        response["error"] = error

    return jsonify(response), (status or 200)

def is_valid_cost(cost):
    """Check if cost is a valid numeric value (not None, not NaN, not empty string)"""
    if cost is None:
        return False
    if isinstance(cost, str):
        if cost.strip() == '' or cost.strip() == '---' or cost.strip() == 'N/A':
            return False
        try:
            float(cost)
            return True
        except ValueError:
            return False
    if isinstance(cost, (int, float)):
        return not math.isnan(cost) and not math.isinf(cost)
    return False

@app.route('/api/resources/stats', methods=['GET'])
def get_resource_stats():
    """
    Get resource statistics, now including parent department stats.
    """
    try:
        # Total number of resources
        total_resources = db[RESOURCES_COLLECTION].count_documents({})
        print(f"Total resources: {total_resources}")

        # Department-wise count
        dept_pipeline = [
            {'$match': {'department': {'$ne': None, '$ne': ''}}},
            {'$group': {'_id': '$department', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        dept_stats = list(db[RESOURCES_COLLECTION].aggregate(dept_pipeline))

        # *** NEW: Parent Department-wise count ***
        parent_dept_pipeline = [
            {'$match': {'parent_department': {'$ne': None, '$ne': ''}}},
            {'$group': {'_id': '$parent_department', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        parent_dept_stats = list(db[RESOURCES_COLLECTION].aggregate(parent_dept_pipeline))

        # Product category-wise count
        category_pipeline = [
            {'$match': {'product_category': {'$ne': None, '$ne': ''}}},
            {'$group': {'_id': '$product_category', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        category_stats = list(db[RESOURCES_COLLECTION].aggregate(category_pipeline))
        print(f"Category stats count: {len(category_stats)}")

        # Section location-wise count
        section_pipeline = [
            {'$match': {'section_location': {'$ne': None, '$ne': ''}}},
            {'$group': {'_id': '$section_location', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        section_stats = list(db[RESOURCES_COLLECTION].aggregate(section_pipeline))
        print(f"Section stats count: {len(section_stats)}")

        # Debug: Check different types of cost values
        cost_analysis = list(db[RESOURCES_COLLECTION].aggregate([
            {'$group': {
                '_id': {'$type': '$cost'},
                'count': {'$sum': 1},
                'sample_values': {'$addToSet': '$cost'}
            }},
            {'$addFields': {
                'sample_values': {'$slice': ['$sample_values', 5]}  # Show first 5 unique values
            }}
        ]))
        print("Cost field analysis:", cost_analysis)

        # More comprehensive cost calculation
        # First, let's identify valid numeric costs
        valid_cost_pipeline = [
            {'$match': {'cost': {'$exists': True}}},
            {'$addFields': {
                'cost_numeric': {
                    '$cond': {
                        'if': {'$in': [{'$type': '$cost'}, ['double', 'int', 'long']]},
                        'then': '$cost',
                        'else': {
                            '$cond': {
                                'if': {'$and': [
                                    {'$eq': [{'$type': '$cost'}, 'string']},
                                    {'$ne': ['$cost', '']}, {'$ne': ['$cost', '---']},
                                    {'$ne': ['$cost', 'N/A']}, {'$ne': ['$cost', 'n/a']}
                                ]},
                                'then': {'$toDouble': '$cost'},
                                'else': None
                            }
                        }
                    }
                }
            }},
            {'$match': {'cost_numeric': {'$ne': None, '$exists': True}}},
            {'$addFields': {'is_valid_number': {'$and': [{'$ne': ['$cost_numeric', float('nan')]}, {'$ne': ['$cost_numeric', float('inf')]}, {'$ne': ['$cost_numeric', float('-inf')]}] }}},
            {'$match': {'is_valid_number': True}},
            {'$group': {
                '_id': None, 'total_cost': {'$sum': '$cost_numeric'},
                'count': {'$sum': 1}, 'avg_cost': {'$avg': '$cost_numeric'},
                'min_cost': {'$min': '$cost_numeric'}, 'max_cost': {'$max': '$cost_numeric'}
            }}
        ]
        cost_result = list(db[RESOURCES_COLLECTION].aggregate(valid_cost_pipeline))

        if cost_result:
            total_cost = cost_result[0].get('total_cost', 0)
            valid_cost_count = cost_result[0].get('count', 0)
            avg_cost = cost_result[0].get('avg_cost', 0)
            min_cost = cost_result[0].get('min_cost', 0)
            max_cost = cost_result[0].get('max_cost', 0)
        else:
            total_cost, valid_cost_count, avg_cost, min_cost, max_cost = 0, 0, 0, 0, 0

        # Department-wise cost calculation (as provided)
        dept_cost_pipeline = [
            {'$match': {'cost': {'$exists': True}}},
            {'$addFields': { # Same conversion logic as above
                'cost_numeric': {
                    '$cond': {
                        'if': {'$in': [{'$type': '$cost'}, ['double', 'int', 'long']]}, 'then': '$cost',
                        'else': {'$cond': {'if': {'$and': [{'$eq': [{'$type': '$cost'}, 'string']}, {'$ne': ['$cost', '']}, {'$ne': ['$cost', '---']}, {'$ne': ['$cost', 'N/A']}]}, 'then': {'$toDouble': '$cost'}, 'else': None }}
                    }
                }
            }},
            {'$match': {'cost_numeric': {'$ne': None, '$exists': True}}},
            {'$group': {
                '_id': '$department',
                'total_cost': {'$sum': '$cost_numeric'},
                'count': {'$sum': 1},
                'valid_cost_count': {'$sum': 1} # Simplified, as all here have valid cost
            }},
            {'$sort': {'total_cost': -1}}
        ]
        dept_cost_stats = list(db[RESOURCES_COLLECTION].aggregate(dept_cost_pipeline))

        excluded_count = total_resources - valid_cost_count

        return format_response(
            data={
                'total_resources': total_resources,
                'total_cost': round(total_cost, 2),
                'valid_cost_count': valid_cost_count,
                'excluded_from_cost': excluded_count,
                'cost_statistics': {
                    'average_cost': round(avg_cost, 2),
                    'min_cost': round(min_cost, 2),
                    'max_cost': round(max_cost, 2)
                },
                'department_stats': dept_stats,
                'parent_department_stats': parent_dept_stats, # Added
                'department_cost_stats': dept_cost_stats,
                'category_stats': category_stats,
                'section_stats': section_stats
            },
            message="Statistics retrieved successfully",
            status=200
        )

    except Exception as e:
        app.logger.error(f"Get resource stats error: {str(e)}")
        return format_response(error=f"Failed to get statistics: {str(e)}", status=500)
# ==================== FILE UPLOAD/EXPORT ROUTES ====================

@app.route('/api/upload-csv', methods=['POST'])
@login_required
@admin_required
def upload_csv():
    try:
        if 'file' not in request.files:
            return format_response(error="No file provided", status=400)
        
        parent_department = request.form.get('parent_department')
        if not parent_department:
            return format_response(error="Parent department is required", status=400)
        
        file = request.files['file']
        return file_service.upload_csv(file, request, parent_department)
    except Exception as e:
        app.logger.error(f"CSV upload error: {str(e)}")
        return format_response(error="CSV upload failed", status=500)

@app.route('/api/upload-excel', methods=['POST'])
@login_required
@admin_required
def upload_excel():
    try:
        if 'file' not in request.files:
            return format_response(error="No file provided", status=400)

        parent_department = request.form.get('parent_department')
        if not parent_department:
            return format_response(error="Parent department is required", status=400)
            
        file = request.files['file']
        return file_service.upload_excel(file, request, parent_department)
    except Exception as e:
        app.logger.error(f"Excel upload error: {str(e)}")
        return format_response(error="Excel upload failed", status=500)

@app.route('/api/export-csv', methods=['GET'])
@login_required
def export_csv():
    try:
        filters = request.args.to_dict()
        return file_service.export_csv(filters)
    except Exception as e:
        app.logger.error(f"CSV export error: {str(e)}")
        return format_response(error="CSV export failed", status=500)

@app.route('/api/export-excel', methods=['GET'])
@login_required
def export_excel():
    try:
        filters = request.args.to_dict()
        return file_service.export_excel(filters)
    except Exception as e:
        app.logger.error(f"Excel export error: {str(e)}")
        return format_response(error="Excel export failed", status=500)
# ==================== AI ROUTES ====================
# in app.py

# In app.py, at the top of the file

from flask import Flask, jsonify, request, make_response, current_app
from datetime import datetime, timezone # <-- CORRECT IMPORT FOR DATETIME
# You can remove 'import datetime' if it's no longer used elsewhere

# ... other imports
from reports import ReportService # Import the new service

# Assume 'app', 'login_required', and 'format_response' are defined elsewhere

@app.route('/api/report/comprehensive-pdf', methods=['GET', 'OPTIONS'])
@login_required
def generate_comprehensive_report():
    """Generate comprehensive PDF report with proper headers"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "Authorization, Content-Type")
        response.headers.add('Access-Control-Allow-Methods', "GET, OPTIONS")
        return response

    try:
        # Get the raw token to pass to the service
        auth_token = get_auth_token_from_request(request)
        if not auth_token:
            return format_response(error="Authorization token is missing or invalid", status=401)

        api_base_url = request.host_url.rstrip('/')
        report_service = ReportService(api_base_url=api_base_url, auth_token=auth_token)

        # Generate the PDF report
        pdf_buffer = report_service.generate_comprehensive_report()

        # Create response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        response.headers['Content-Disposition'] = f'attachment; filename=MSRIT_Comprehensive_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return response

    except Exception as e:
        # Using logger is great for debugging
        # current_app.logger.error(f"Report generation error: {str(e)}", exc_info=True)
        print(f"Report generation error: {str(e)}") # Use print if logger is not set up
        return format_response(error=f"Failed to generate report: An internal error occurred.", status=500)



def get_auth_token_from_request(req):
    """Extracts the JWT token string from the request headers."""
    auth_header = req.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    return None
# The test route can remain as is, or be updated for consistency
@app.route('/api/report/test-pdf', methods=['GET', 'OPTIONS'])
@login_required   
def generate_test_report():
    """Generate a simple test PDF"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response
         
    try:
        from fpdf import FPDF
        from io import BytesIO
         
        # Create simple PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Test PDF Report', 0, 1, 'C')
        pdf.ln(10)
         
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 8, f'Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
        pdf.cell(0, 8, 'This is a test PDF to verify download functionality.', 0, 1)
         
        # Output PDF
        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)
         
        response = make_response(pdf_output.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        response.headers['Content-Disposition'] = f'attachment; filename=test_report_{datetime.datetime.now().strftime("%Y%m%d")}.pdf'
         
        return response
         
    except Exception as e:
        current_app.logger.error(f"Test report generation error: {str(e)}")
        return format_response(error=f"Failed to generate test report: {str(e)}", status=500)
    
@app.route('/api/ai/natural-crud', methods=['POST'])
@login_required
@admin_required
def natural_crud():
    try:
        data = request.get_json()
        validation_error = validate_request_data(data, ['instruction'])
        if validation_error:
            return validation_error
        
        return ai_service.natural_crud(data, request)
    except Exception as e:
        app.logger.error(f"Natural CRUD error: {str(e)}")
        return format_response(error="Natural CRUD operation failed", status=400)

@app.route('/api/ai/chat', methods=['POST'])
@login_required
def chat():
    try:
        data = request.get_json()
        validation_error = validate_request_data(data, ['message'])
        if validation_error:
            return validation_error
        
        return ai_service.chat(data, request)
    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        return format_response(error="Chat request failed", status=400)

@app.route('/api/ai/chat/history', methods=['GET'])
@login_required
def chat_history():
    try:
        user_id = request.args.get('user_id')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        return ai_service.chat_history(user_id, page, limit, request)
    except Exception as e:
        app.logger.error(f"Chat history error: {str(e)}")
        return format_response(error="Failed to fetch chat history", status=400)

# ==================== DASHBOARD ROUTES ====================

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    try:
        return resource_service.dashboard_stats()
    except Exception as e:
        app.logger.error(f"Dashboard stats error: {str(e)}")
        return format_response(error="Failed to fetch dashboard stats", status=400)

@app.route('/api/dashboard/charts', methods=['GET'])
@login_required
def dashboard_charts():
    try:
        chart_type = request.args.get('type', 'all')
        return resource_service.dashboard_charts(chart_type)
    except Exception as e:
        app.logger.error(f"Dashboard charts error: {str(e)}")
        return format_response(error="Failed to fetch chart data", status=400)

@app.route('/api/dashboard/recent-activity', methods=['GET'])
@login_required
def recent_activity():
    try:
        limit = int(request.args.get('limit', 10))
        return resource_service.recent_activity(limit)
    except Exception as e:
        app.logger.error(f"Recent activity error: {str(e)}")
        return format_response(error="Failed to fetch recent activity", status=400)

# ==================== UTILITY ROUTES ====================

# @app.route('/api/locations', methods=['GET'])
# @login_required
# def get_locations():
#     try:
#         return resource_service.get_unique_values('location')
#     except Exception as e:
#         app.logger.error(f"Get locations error: {str(e)}")
#         return format_response(error="Failed to fetch locations", status=400)

# @app.route('/api/departments', methods=['GET'])
# @login_required
# def get_departments():
#     try:
#         return resource_service.get_unique_values('department')
#     except Exception as e:
#         app.logger.error(f"Get departments error: {str(e)}")
#         return format_response(error="Failed to fetch departments", status=400)

# ==================== ADMIN VERIFICATION WEB ROUTES ====================

@app.route('/admin-verify', methods=['GET'])
def admin_verify_page():
    """Serve admin verification page"""
    email = request.args.get('email')
    if not email:
        return """
        <html>
        <head><title>Admin Verification</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h2 style="color: #e74c3c;">❌ Error</h2>
            <p>No email specified for verification.</p>
            <a href="/" style="color: #3498db;">← Back to Home</a>
        </body>
        </html>
        """
    
    # Check if user exists and is admin
    try:
        if db is None:
            return """
            <html>
            <head><title>Admin Verification</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h2 style="color: #e74c3c;">❌ Database Error</h2>
                <p>Database connection not available.</p>
                <a href="/" style="color: #3498db;">← Back to Home</a>
            </body>
            </html>
            """
        
        user = db[USERS_COLLECTION].find_one({'email': email, 'role': ADMIN_ROLE})
        if not user:
            return f"""
            <html>
            <head><title>Admin Verification</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h2 style="color: #e74c3c;">❌ Error</h2>
                <p>Admin user not found: {email}</p>
                <a href="/" style="color: #3498db;">← Back to Home</a>
            </body>
            </html>
            """
        
        if user['status'] == USER_STATUS_APPROVED:
            return f"""
            <html>
            <head><title>Admin Verification</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h2 style="color: #27ae60;">✅ Already Approved</h2>
                <p>Admin user <strong>{email}</strong> is already approved.</p>
                <div style="background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Name:</strong> {user.get('name', 'N/A')}</p>
                    <p><strong>Email:</strong> {user['email']}</p>
                    <p><strong>Role:</strong> {user['role']}</p>
                    <p><strong>Status:</strong> {user['status']}</p>
                    <p><strong>Created:</strong> {user['created_at'].strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                </div>
                <a href="/" style="color: #3498db;">← Back to Home</a>
            </body>
            </html>
            """
        
        # Show verification form
        return f"""
        <html>
        <head>
            <title>Admin Verification - Campus Assets</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f8f9fa; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .user-info {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .buttons {{ text-align: center; margin: 30px 0; }}
                .btn {{ padding: 12px 30px; margin: 0 10px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; }}
                .btn-approve {{ background: #27ae60; color: white; }}
                .btn-reject {{ background: #e74c3c; color: white; }}
                .btn:hover {{ opacity: 0.8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="color: #2c3e50;">🔐 Admin Account Verification</h1>
                    <p>Please review and approve/reject this admin account request:</p>
                </div>
                
                <div class="user-info">
                    <h3>User Details:</h3>
                    <p><strong>Name:</strong> {user.get('name', 'N/A')}</p>
                    <p><strong>Email:</strong> {user['email']}</p>
                    <p><strong>Role:</strong> {user['role']}</p>
                    <p><strong>Current Status:</strong> {user['status']}</p>
                    <p><strong>Registration Date:</strong> {user['created_at'].strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                </div>
                
                <div class="buttons">
                    <a href="/admin-verify-action?email={email}&action=approve" class="btn btn-approve">
                        ✅ Approve Admin
                    </a>
                    <a href="/admin-verify-action?email={email}&action=reject" class="btn btn-reject">
                        ❌ Reject Admin
                    </a>
                </div>
                
                <p style="text-align: center; color: #7f8c8d; margin-top: 30px;">
                    Campus Assets Management System
                </p>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html>
        <head><title>Admin Verification</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h2 style="color: #e74c3c;">❌ Error</h2>
            <p>An error occurred: {str(e)}</p>
            <a href="/" style="color: #3498db;">← Back to Home</a>
        </body>
        </html>
        """

@app.route('/admin-verify-action', methods=['GET'])
def admin_verify_action():
    """Handle admin approval/rejection"""
    email = request.args.get('email')
    action = request.args.get('action')
    
    if not email or not action:
        return """
        <html>
        <head><title>Admin Verification</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h2 style="color: #e74c3c;">❌ Error</h2>
            <p>Missing email or action parameter.</p>
            <a href="/" style="color: #3498db;">← Back to Home</a>
        </body>
        </html>
        """
    
    try:
        if db is None:
            return """
            <html>
            <head><title>Admin Verification</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h2 style="color: #e74c3c;">❌ Database Error</h2>
                <p>Database connection not available.</p>
                <a href="/" style="color: #3498db;">← Back to Home</a>
            </body>
            </html>
            """
        
        user = db[USERS_COLLECTION].find_one({'email': email, 'role': ADMIN_ROLE})
        if not user:
            return f"""
            <html>
            <head><title>Admin Verification</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h2 style="color: #e74c3c;">❌ Error</h2>
                <p>Admin user not found: {email}</p>
                <a href="/" style="color: #3498db;">← Back to Home</a>
            </body>
            </html>
            """
        
        if action == 'approve':
            # Approve the admin
            db[USERS_COLLECTION].update_one(
                {'email': email},
                {'$set': {'status': USER_STATUS_APPROVED}}
            )
            
            # Send approval notification email
            try:
                auth_service.send_approval_notification(email, user.get('name', ''), approved=True)
            except:
                pass  # Don't fail if email doesn't work
            
            return f"""
            <html>
            <head>
                <title>Admin Approved - Campus Assets</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f8f9fa; }}
                    .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 style="color: #27ae60;">✅ Admin Approved Successfully!</h1>
                    <p>Admin user <strong>{email}</strong> has been approved and can now access the system.</p>
                    <p>The user has been notified via email.</p>
                    <div style="background: #d5f4e6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Action:</strong> Approved</p>
                        <p><strong>Admin Email:</strong> {email}</p>
                        <p><strong>Admin Name:</strong> {user.get('name', 'N/A')}</p>
                        <p><strong>Timestamp:</strong> {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                    </div>
                    <a href="/" style="color: #3498db;">← Back to Home</a>
                </div>
            </body>
            </html>
            """
            
        elif action == 'reject':
            # Reject the admin
            db[USERS_COLLECTION].update_one(
                {'email': email},
                {'$set': {'status': USER_STATUS_REJECTED}}
            )
            
            # Send rejection notification email
            try:
                auth_service.send_approval_notification(email, user.get('name', ''), approved=False)
            except:
                pass  # Don't fail if email doesn't work
            
            return f"""
            <html>
            <head>
                <title>Admin Rejected - Campus Assets</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f8f9fa; }}
                    .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 style="color: #e74c3c;">❌ Admin Rejected</h1>
                    <p>Admin user <strong>{email}</strong> has been rejected.</p>
                    <p>The user has been notified via email.</p>
                    <div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Action:</strong> Rejected</p>
                        <p><strong>Admin Email:</strong> {email}</p>
                        <p><strong>Admin Name:</strong> {user.get('name', 'N/A')}</p>
                        <p><strong>Timestamp:</strong> {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                    </div>
                    <a href="/" style="color: #3498db;">← Back to Home</a>
                </div>
            </body>
            </html>
            """
        else:
            return """
            <html>
            <head><title>Admin Verification</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h2 style="color: #e74c3c;">❌ Error</h2>
                <p>Invalid action. Must be 'approve' or 'reject'.</p>
                <a href="/" style="color: #3498db;">← Back to Home</a>
            </body>
            </html>
            """
            
    except Exception as e:
        return f"""
        <html>
        <head><title>Admin Verification</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h2 style="color: #e74c3c;">❌ Error</h2>
            <p>An error occurred: {str(e)}</p>
            <a href="/" style="color: #3498db;">← Back to Home</a>
        </body>
        </html>
        """


@app.route('/', methods=['GET'])
def home():
    """Simple home page"""
    return """
    <html>
    <head>
        <title>Campus Assets Management System</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #f8f9fa; }
            .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="color: #2c3e50;">🏫 Campus Assets Management System</h1>
            <p>Backend API is running successfully!</p>
            <div style="background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3>Available Endpoints:</h3>
                <p><strong>Health Check:</strong> <a href="/api/health">/api/health</a></p>
                <p><strong>API Documentation:</strong> Coming soon with frontend</p>
            </div>
            <p style="color: #7f8c8d;">Use the test CLI or connect your frontend application</p>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
