# Campus Assets Management API Reference

## Base URL

- Development: http://127.0.0.1:5000
- Production: https://campusassets.onrender.com

## Authentication

- Uses JWT tokens in Authorization header: `Bearer `
- Firebase authentication integration
- Session-based authentication

## User Roles

- **Admin**: Full CRUD access, file uploads, AI features
- **Viewer**: Read-only access, chat features

## API Endpoints

### Authentication

- POST /api/auth/register - User registration
- POST /api/auth/login - User login with Firebase token
- POST /api/auth/logout - User logout
- GET /api/auth/profile - Get user profile
- GET /api/auth/verify-admin - Admin verification

### Resources

- GET /api/resources - List resources (with pagination and filters)
- POST /api/resources - Create resource (Admin only)
- GET /api/resources/:id - Get specific resource
- PUT /api/resources/:id - Update resource (Admin only)
- DELETE /api/resources/:id - Delete resource (Admin only)
- GET /api/resources/search - Search resources

### File Operations

- POST /api/upload/csv - Upload CSV file (Admin only)
- POST /api/upload/excel - Upload Excel file (Admin only)
- GET /api/export/csv - Export data as CSV
- GET /api/export/excel - Export data as Excel

### AI Features

- POST /api/ai/natural-crud - Natural language CRUD operations (Admin only)
- POST /api/ai/chat - Chat with AI assistant
- GET /api/ai/chat/history - Get chat history

### Dashboard

- GET /api/dashboard/stats - Dashboard statistics
- GET /api/dashboard/charts - Chart data
- GET /api/dashboard/recent-activity - Recent activity

### Utilities

- GET /api/locations - Get unique locations
- GET /api/departments - Get unique departments

## Resource Schema

```

{
"sl_no": "string",
"description": "string",
"service_tag": "string",
"identification_number": "string",
"procurement_date": "YYYY-MM-DD",
"cost": "number",
"location": "string",
"department": "string"
}

```

## Response Format

All APIs return:

```

{
"data": {},
"message": "string",
"error": "string",
"status": 200,
"timestamp": "ISO datetime"
}

```
