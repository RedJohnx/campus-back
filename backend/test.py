import requests
import json
import os
from datetime import datetime

BASE_URL = 'https://campusassets.onrender.com'

class TestCLI:
    def __init__(self):
        self.session_token = None
        self.user_data = None
    
    def run(self):
        print("=" * 50)
        print("🚀 Resource Management Backend Test CLI")
        print("=" * 50)
        
        while True:
            self.show_menu()
            choice = input("\n🔹 Enter your choice: ").strip()
            
            if choice == '1':
                self.test_health()
            elif choice == '2':
                self.test_register()
            elif choice == '3':
                self.test_login()
            elif choice == '4':
                self.test_verify_admin()
            elif choice == '5':
                self.test_crud_operations()
            elif choice == '6':
                self.test_file_operations()
            elif choice == '7':
                self.test_ai_features()
            elif choice == '8':
                self.test_dashboard()
            elif choice == '9':
                self.test_search_filter()
            elif choice == '10':
                self.test_profile()
            elif choice == '11':
                self.test_logout()
            elif choice == '0':
                print("\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please try again.")
    
    def show_menu(self):
        print(f"\n{'='*50}")
        print("📋 MAIN MENU")
        print("=" * 50)
        print("1. 🏥 Health Check")
        print("2. 👤 Register User")
        print("3. 🔐 Login User")
        print("4. ✅ Verify Admin")
        print("5. 📊 CRUD Operations")
        print("6. 📁 File Operations")
        print("7. 🤖 AI Features")
        print("8. 📈 Dashboard")
        print("9. 🔍 Search & Filter")
        print("10. 👤 Profile")
        print("11. 🚪 Logout")
        print("0. ❌ Exit")
        
        if self.session_token:
            print(f"\n✅ Logged in as: {self.user_data.get('email', 'Unknown') if self.user_data else 'Unknown'}")
        else:
            print("\n⚠️  Not logged in")
    
    def test_health(self):
        print("\n🏥 Testing Health Check...")
        try:
            response = requests.get(f'{BASE_URL}/api/health')
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_register(self):
        print("\n👤 User Registration")
        print("-" * 30)
        
        email = input("📧 Email: ").strip()
        password = input("🔒 Password: ").strip()
        name = input("👤 Name: ").strip()
        
        print("\n🔹 Select Role:")
        print("1. Admin")
        print("2. Viewer")
        role_choice = input("Choice: ").strip()
        
        role = 'admin' if role_choice == '1' else 'viewer'
        
        data = {
            'email': email,
            'password': password,
            'name': name,
            'role': role
        }
        
        try:
            response = requests.post(f'{BASE_URL}/api/auth/register', json=data)
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_login(self):
        print("\n🔐 User Login")
        print("-" * 30)
        
        # For testing, we'll simulate a Firebase ID token
        email = input("📧 Email: ").strip()
        
        # Simulate Firebase ID token (in real app, this comes from Firebase)
        id_token = f"simulated_firebase_token_{email}"
        
        data = {'idToken': id_token}
        
        try:
            response = requests.post(f'{BASE_URL}/api/auth/login', json=data)
            
            if response.status_code == 200:
                result = response.json()
                self.session_token = result.get('data', {}).get('session_token')
                self.user_data = result.get('data', {}).get('user')
                print("✅ Login successful!")
            
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_verify_admin(self):
        print("\n✅ Admin Verification")
        print("-" * 30)
        
        email = input("📧 Admin Email to verify: ").strip()
        
        try:
            response = requests.get(f'{BASE_URL}/api/auth/verify-admin', params={'token': email})
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_crud_operations(self):
        if not self.session_token:
            print("❌ Please login first!")
            return
        
        print("\n📊 CRUD Operations")
        print("-" * 30)
        print("1. Create Resource")
        print("2. Get Resources")
        print("3. Get Single Resource")
        print("4. Update Resource")
        print("5. Delete Resource")
        
        choice = input("Choice: ").strip()
        
        if choice == '1':
            self.test_create_resource()
        elif choice == '2':
            self.test_get_resources()
        elif choice == '3':
            self.test_get_single_resource()
        elif choice == '4':
            self.test_update_resource()
        elif choice == '5':
            self.test_delete_resource()
    
    def test_create_resource(self):
        print("\n➕ Create Resource")
        print("-" * 30)
        
        data = {}
        data['sl_no'] = input("SL No: ").strip()
        data['description'] = input("Description: ").strip()
        data['service_tag'] = input("Service Tag: ").strip()
        data['identification_number'] = input("Identification Number: ").strip()
        data['procurement_date'] = input("Procurement Date (YYYY-MM-DD): ").strip()
        data['cost'] = float(input("Cost: ").strip())
        data['location'] = input("Location: ").strip()
        data['department'] = input("Department: ").strip()
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.post(f'{BASE_URL}/api/resources', json=data, headers=headers)
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_get_resources(self):
        print("\n📋 Get Resources")
        print("-" * 30)
        
        # Optional filters
        location = input("Location filter (optional): ").strip()
        department = input("Department filter (optional): ").strip()
        
        params = {}
        if location:
            params['location'] = location
        if department:
            params['department'] = department
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.get(f'{BASE_URL}/api/resources', params=params, headers=headers)
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_get_single_resource(self):
        print("\n🔍 Get Single Resource")
        print("-" * 30)
        
        resource_id = input("Resource ID: ").strip()
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.get(f'{BASE_URL}/api/resources/{resource_id}', headers=headers)
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_update_resource(self):
        print("\n✏️ Update Resource")
        print("-" * 30)
        
        resource_id = input("Resource ID: ").strip()
        
        data = {}
        print("Enter fields to update (leave blank to skip):")
        
        fields = ['sl_no', 'description', 'service_tag', 'identification_number', 
                 'procurement_date', 'cost', 'location', 'department']
        
        for field in fields:
            value = input(f"{field}: ").strip()
            if value:
                if field == 'cost':
                    data[field] = float(value)
                else:
                    data[field] = value
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.put(f'{BASE_URL}/api/resources/{resource_id}', json=data, headers=headers)
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_delete_resource(self):
        print("\n🗑️ Delete Resource")
        print("-" * 30)
        
        resource_id = input("Resource ID: ").strip()
        
        confirm = input("Are you sure? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Cancelled")
            return
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.delete(f'{BASE_URL}/api/resources/{resource_id}', headers=headers)
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_file_operations(self):
        if not self.session_token:
            print("❌ Please login first!")
            return
        
        print("\n📁 File Operations")
        print("-" * 30)
        print("1. Upload CSV")
        print("2. Upload Excel")
        print("3. Export CSV")
        print("4. Export Excel")
        
        choice = input("Choice: ").strip()
        
        if choice == '1':
            self.test_upload_csv()
        elif choice == '2':
            self.test_upload_excel()
        elif choice == '3':
            self.test_export_csv()
        elif choice == '4':
            self.test_export_excel()
    
    def test_upload_csv(self):
        print("\n📤 Upload CSV")
        print("-" * 30)
        
        filepath = input("CSV file path: ").strip()
        
        if not os.path.exists(filepath):
            print("❌ File not found!")
            return
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            with open(filepath, 'rb') as f:
                files = {'file': f}
                response = requests.post(f'{BASE_URL}/api/upload/csv', files=files, headers=headers)
                self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_upload_excel(self):
        print("\n📤 Upload Excel")
        print("-" * 30)
        
        filepath = input("Excel file path: ").strip()
        
        if not os.path.exists(filepath):
            print("❌ File not found!")
            return
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            with open(filepath, 'rb') as f:
                files = {'file': f}
                response = requests.post(f'{BASE_URL}/api/upload/excel', files=files, headers=headers)
                self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_export_csv(self):
        print("\n📥 Export CSV")
        print("-" * 30)
        
        location = input("Location filter (optional): ").strip()
        department = input("Department filter (optional): ").strip()
        
        params = {}
        if location:
            params['location'] = location
        if department:
            params['department'] = department
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.get(f'{BASE_URL}/api/export/csv', params=params, headers=headers)
            
            if response.status_code == 200:
                filename = f"exported_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅ CSV exported to {filename}")
            else:
                self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_export_excel(self):
        print("\n📥 Export Excel")
        print("-" * 30)
        
        location = input("Location filter (optional): ").strip()
        department = input("Department filter (optional): ").strip()
        
        params = {}
        if location:
            params['location'] = location
        if department:
            params['department'] = department
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.get(f'{BASE_URL}/api/export/excel', params=params, headers=headers)
            
            if response.status_code == 200:
                filename = f"exported_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Excel exported to {filename}")
            else:
                self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_ai_features(self):
        if not self.session_token:
            print("❌ Please login first!")
            return
        
        print("\n🤖 AI Features")
        print("-" * 30)
        print("1. Natural Language CRUD")
        print("2. AI Chat")
        print("3. Chat History")
        
        choice = input("Choice: ").strip()
        
        if choice == '1':
            self.test_natural_crud()
        elif choice == '2':
            self.test_ai_chat()
        elif choice == '3':
            self.test_chat_history()
    
    def test_natural_crud(self):
        print("\n🗣️ Natural Language CRUD")
        print("-" * 30)
        
        instruction = input("Enter your instruction: ").strip()
        
        data = {'instruction': instruction}
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.post(f'{BASE_URL}/api/ai/natural-crud', json=data, headers=headers)
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_ai_chat(self):
        print("\n💬 AI Chat")
        print("-" * 30)
        
        message = input("Enter your message: ").strip()
        
        data = {'message': message}
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.post(f'{BASE_URL}/api/ai/chat', json=data, headers=headers)
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_chat_history(self):
        print("\n📜 Chat History")
        print("-" * 30)
        
        user_id = input("User ID (leave blank for your history): ").strip()
        
        params = {}
        if user_id:
            params['user_id'] = user_id
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.get(f'{BASE_URL}/api/ai/chat/history', params=params, headers=headers)
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_dashboard(self):
        if not self.session_token:
            print("❌ Please login first!")
            return
        
        print("\n📈 Dashboard")
        print("-" * 30)
        print("1. Dashboard Stats")
        print("2. Dashboard Charts")
        print("3. Recent Activity")
        
        choice = input("Choice: ").strip()
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            if choice == '1':
                response = requests.get(f'{BASE_URL}/api/dashboard/stats', headers=headers)
            elif choice == '2':
                response = requests.get(f'{BASE_URL}/api/dashboard/charts', headers=headers)
            elif choice == '3':
                response = requests.get(f'{BASE_URL}/api/dashboard/recent-activity', headers=headers)
            else:
                print("❌ Invalid choice")
                return
            
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_search_filter(self):
        if not self.session_token:
            print("❌ Please login first!")
            return
        
        print("\n🔍 Search & Filter")
        print("-" * 30)
        print("1. Search Resources")
        print("2. Get Locations")
        print("3. Get Departments")
        
        choice = input("Choice: ").strip()
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            if choice == '1':
                query = input("Search query: ").strip()
                params = {'q': query}
                response = requests.get(f'{BASE_URL}/api/resources/search', params=params, headers=headers)
            elif choice == '2':
                response = requests.get(f'{BASE_URL}/api/locations', headers=headers)
            elif choice == '3':
                response = requests.get(f'{BASE_URL}/api/departments', headers=headers)
            else:
                print("❌ Invalid choice")
                return
            
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_profile(self):
        if not self.session_token:
            print("❌ Please login first!")
            return
        
        print("\n👤 Profile")
        print("-" * 30)
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.get(f'{BASE_URL}/api/auth/profile', headers=headers)
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_logout(self):
        if not self.session_token:
            print("❌ Not logged in!")
            return
        
        print("\n🚪 Logout")
        print("-" * 30)
        
        headers = {'Authorization': f'Bearer {self.session_token}'}
        
        try:
            response = requests.post(f'{BASE_URL}/api/auth/logout', headers=headers)
            
            if response.status_code == 200:
                self.session_token = None
                self.user_data = None
                print("✅ Logged out successfully!")
            
            self.print_response(response)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def print_response(self, response):
        """Print formatted response"""
        print(f"\n📊 Response Status: {response.status_code}")
        print("-" * 50)
        
        try:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(response.text)
        
        print("-" * 50)
        
        # Status indicator
        if response.status_code < 300:
            print("✅ Success")
        elif response.status_code < 400:
            print("🔄 Redirect")
        elif response.status_code < 500:
            print("⚠️  Client Error")
        else:
            print("❌ Server Error")

if __name__ == '__main__':
    cli = TestCLI()
    cli.run()
