from functools import wraps
from flask import request, jsonify
import re
import jwt
from datetime import datetime

from config import JWT_SECRET, ADMIN_ROLE, VIEWER_ROLE, db, SESSIONS_COLLECTION

def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def format_response(data=None, message=None, error=None, status=200):
    """Format standard API response"""
    response = {}
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    if error:
        response['error'] = error
    
    response['status'] = status
    response['timestamp'] = datetime.utcnow().isoformat()
    
    return jsonify(response), status

def validate_request_data(data, required_fields):
    """Validate required fields in request data"""
    if not data:
        return format_response(error="No data provided", status=400)
    
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        return format_response(
            error=f"Missing required fields: {', '.join(missing_fields)}",
            status=400
        )
    
    return None

def get_user_from_token(request):
    """Extract user data from JWT token"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        # Decode JWT token
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        # Check if session exists in database
        session = db[SESSIONS_COLLECTION].find_one({'session_token': token})
        if not session:
            return None
        
        # Check if session is expired
        if session['expires_at'] < datetime.utcnow():
            # Remove expired session
            db[SESSIONS_COLLECTION].delete_one({'session_token': token})
            return None
        
        return decoded_token
        
    except Exception as e:
        print(f"Token validation error: {e}")
        return None

def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_data = get_user_from_token(request)
        if not user_data:
            return format_response(error="Authentication required", status=401)
        
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_data = get_user_from_token(request)
        if not user_data:
            return format_response(error="Authentication required", status=401)
        
        if user_data.get('role') != ADMIN_ROLE:
            return format_response(error="Admin privileges required", status=403)
        
        return f(*args, **kwargs)
    
    return decorated_function

def viewer_or_admin_required(f):
    """Decorator to require viewer or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_data = get_user_from_token(request)
        if not user_data:
            return format_response(error="Authentication required", status=401)
        
        if user_data.get('role') not in [ADMIN_ROLE, VIEWER_ROLE]:
            return format_response(error="Insufficient privileges", status=403)
        
        return f(*args, **kwargs)
    
    return decorated_function

def sanitize_input(input_string):
    """Sanitize user input"""
    if not input_string:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', str(input_string))
    return sanitized.strip()

def validate_object_id(object_id):
    """Validate MongoDB ObjectId format"""
    if not object_id:
        return False
    
    # Check if it's a valid ObjectId format
    return re.match(r'^[a-fA-F0-9]{24}$', object_id) is not None

def paginate_query(query, page, limit):
    """Apply pagination to MongoDB query"""
    skip = (page - 1) * limit
    return query.skip(skip).limit(limit)

def build_search_query(search_term, fields):
    """Build MongoDB search query"""
    if not search_term:
        return {}
    
    search_conditions = []
    for field in fields:
        search_conditions.append({
            field: {'$regex': search_term, '$options': 'i'}
        })
    
    return {'$or': search_conditions}

def validate_date_format(date_string):
    """Validate date format (YYYY-MM-DD)"""
    if not date_string:
        return False
    
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_cost(cost_value):
    """Validate cost value"""
    try:
        cost = float(cost_value)
        return cost >= 0
    except (ValueError, TypeError):
        return False

def clean_resource_data(data):
    """Clean and validate resource data"""
    cleaned_data = {}
    
    # List of allowed fields
    allowed_fields = [
        'sl_no', 'description', 'service_tag', 'identification_number',
        'procurement_date', 'cost', 'location', 'department'
    ]
    
    for field in allowed_fields:
        if field in data:
            if field == 'cost':
                if validate_cost(data[field]):
                    cleaned_data[field] = float(data[field])
            elif field == 'procurement_date':
                if validate_date_format(data[field]):
                    cleaned_data[field] = data[field]
            else:
                cleaned_data[field] = sanitize_input(data[field])
    
    return cleaned_data

def log_activity(user_id, action, resource_id=None, details=None):
    """Log user activity"""
    try:
        activity_doc = {
            'user_id': user_id,
            'action': action,
            'resource_id': resource_id,
            'details': details,
            'timestamp': datetime.utcnow()
        }
        
        db.activity_logs.insert_one(activity_doc)
        
    except Exception as e:
        print(f"Failed to log activity: {e}")

def generate_session_token(user_data):
    """Generate JWT session token"""
    try:
        payload = {
            'uid': user_data['uid'],
            'email': user_data['email'],
            'role': user_data['role'],
            'exp': datetime.utcnow() + datetime.timedelta(hours=8)
        }
        
        return jwt.encode(payload, JWT_SECRET, algorithm='HS256')
        
    except Exception as e:
        print(f"Failed to generate session token: {e}")
        return None

def validate_filters(filters):
    """Validate and clean filter parameters"""
    cleaned_filters = {}
    
    # Allowed filter fields
    allowed_filters = ['location', 'department', 'cost_min', 'cost_max', 'search']
    
    for key, value in filters.items():
        if key in allowed_filters and value:
            if key in ['cost_min', 'cost_max']:
                if validate_cost(value):
                    cleaned_filters[key] = float(value)
            else:
                cleaned_filters[key] = sanitize_input(value)
    
    return cleaned_filters

def create_export_filename(base_name, filters):
    """Create filename for exports based on filters"""
    filename = base_name
    
    if filters.get('location'):
        filename += f"_{filters['location']}"
    
    if filters.get('department'):
        filename += f"_{filters['department']}"
    
    # Add timestamp
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename += f"_{timestamp}"
    
    return filename

def validate_csv_headers(headers, required_headers):
    """Validate CSV headers"""
    missing_headers = []
    
    for required in required_headers:
        if required not in headers:
            missing_headers.append(required)
    
    return missing_headers

def process_csv_row(row, row_number):
    """Process a single CSV row and return errors if any"""
    errors = []
    
    # Validate required fields
    required_fields = ['SL No', 'Description', 'Service Tag', 'Identification Number', 
                      'Procurement Date', 'Cost', 'Location', 'Department']
    
    for field in required_fields:
        if not row.get(field) or str(row[field]).strip() == '':
            errors.append(f"Row {row_number}: Missing {field}")
    
    # Validate cost
    if 'Cost' in row and row['Cost']:
        if not validate_cost(row['Cost']):
            errors.append(f"Row {row_number}: Invalid cost value")
    
    # Validate date
    if 'Procurement Date' in row and row['Procurement Date']:
        if not validate_date_format(str(row['Procurement Date'])):
            errors.append(f"Row {row_number}: Invalid date format (use YYYY-MM-DD)")
    
    return errors

def calculate_pagination_info(total_items, page, limit):
    """Calculate pagination information"""
    total_pages = (total_items + limit - 1) // limit
    
    return {
        'page': page,
        'limit': limit,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }
