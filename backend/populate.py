import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import random

def create_sample_csv():
    """Create a sample CSV file with resource data"""
    
    # Sample data for different departments and locations
    sample_data = [
        {
            'SL No': '001',
            'Description': 'Dell OptiPlex 7090 Desktop',
            'Service Tag': 'DT001SRV',
            'Identification Number': 'CSE-DT-001',
            'Procurement Date': '2023-01-15',
            'Cost': 45000.0,
            'Location': 'CSE Lab 1',
            'Department': 'CSE'
        },
        {
            'SL No': '002',
            'Description': 'HP LaserJet Pro Printer',
            'Service Tag': 'HP002PRT',
            'Identification Number': 'CSE-PR-001',
            'Procurement Date': '2022-11-20',
            'Cost': 12000.0,
            'Location': 'CSE Lab 1',
            'Department': 'CSE'
        },
        {
            'SL No': '003',
            'Description': 'Dell 24-inch Monitor',
            'Service Tag': 'DL003MON',
            'Identification Number': 'CSE-MN-001',
            'Procurement Date': '2023-03-10',
            'Cost': 15000.0,
            'Location': 'CSE Lab 2',
            'Department': 'CSE'
        },
        {
            'SL No': '004',
            'Description': 'Cisco Catalyst 2960 Switch',
            'Service Tag': 'CS004NET',
            'Identification Number': 'ECE-NT-001',
            'Procurement Date': '2023-02-05',
            'Cost': 35000.0,
            'Location': 'ECE Network Lab',
            'Department': 'ECE'
        },
        {
            'SL No': '005',
            'Description': 'Oscilloscope - Tektronix',
            'Service Tag': 'TK005OSC',
            'Identification Number': 'EEE-OS-001',
            'Procurement Date': '2022-12-18',
            'Cost': 125000.0,
            'Location': 'EEE Electronics Lab',
            'Department': 'EEE'
        },
        {
            'SL No': '006',
            'Description': 'HP Workstation Z440',
            'Service Tag': 'HP006WKS',
            'Identification Number': 'CSE-WS-001',
            'Procurement Date': '2023-01-25',
            'Cost': 85000.0,
            'Location': 'CSE Research Lab',
            'Department': 'CSE'
        },
        {
            'SL No': '007',
            'Description': 'Projector - Epson EB-X05',
            'Service Tag': 'EP007PRJ',
            'Identification Number': 'GEN-PJ-001',
            'Procurement Date': '2022-10-12',
            'Cost': 28000.0,
            'Location': 'Auditorium',
            'Department': 'General'
        },
        {
            'SL No': '008',
            'Description': 'Network Attached Storage',
            'Service Tag': 'SY008NAS',
            'Identification Number': 'IT-ST-001',
            'Procurement Date': '2023-04-20',
            'Cost': 95000.0,
            'Location': 'Server Room',
            'Department': 'IT'
        },
        {
            'SL No': '009',
            'Description': 'UPS - APC Smart-UPS',
            'Service Tag': 'AP009UPS',
            'Identification Number': 'GEN-UP-001',
            'Procurement Date': '2022-09-30',
            'Cost': 22000.0,
            'Location': 'Main Power Room',
            'Department': 'General'
        },
        {
            'SL No': '010',
            'Description': 'Server - Dell PowerEdge R740',
            'Service Tag': 'DL010SRV',
            'Identification Number': 'IT-SV-001',
            'Procurement Date': '2023-05-15',
            'Cost': 180000.0,
            'Location': 'Data Center',
            'Department': 'IT'
        },
        {
            'SL No': '011',
            'Description': 'Laptop - ThinkPad X1 Carbon',
            'Service Tag': 'LN011LAP',
            'Identification Number': 'CSE-LP-001',
            'Procurement Date': '2023-06-01',
            'Cost': 95000.0,
            'Location': 'Faculty Room',
            'Department': 'CSE'
        },
        {
            'SL No': '012',
            'Description': 'Digital Multimeter',
            'Service Tag': 'FL012DMM',
            'Identification Number': 'EEE-DM-001',
            'Procurement Date': '2022-08-14',
            'Cost': 8500.0,
            'Location': 'EEE Lab 3',
            'Department': 'EEE'
        },
        {
            'SL No': '013',
            'Description': 'Spectrum Analyzer',
            'Service Tag': 'KS013SPA',
            'Identification Number': 'ECE-SA-001',
            'Procurement Date': '2023-02-28',
            'Cost': 145000.0,
            'Location': 'ECE RF Lab',
            'Department': 'ECE'
        },
        {
            'SL No': '014',
            'Description': 'Industrial Robot Arm',
            'Service Tag': 'KB014ROB',
            'Identification Number': 'ME-RB-001',
            'Procurement Date': '2023-03-22',
            'Cost': 450000.0,
            'Location': 'Mechanical Lab',
            'Department': 'ME'
        },
        {
            'SL No': '015',
            'Description': 'Air Conditioning Unit',
            'Service Tag': 'LG015AC',
            'Identification Number': 'GEN-AC-001',
            'Procurement Date': '2022-05-10',
            'Cost': 65000.0,
            'Location': 'Computer Lab',
            'Department': 'General'
        }
    ]
    
    # Create DataFrame
    df = pd.DataFrame(sample_data)
    
    # Save to CSV
    csv_filename = 'campus_resources_sample.csv'
    df.to_csv(csv_filename, index=False)
    
    print(f"✅ Created CSV file: {csv_filename}")
    print(f"📊 Total records: {len(sample_data)}")
    print(f"🏢 Departments: {', '.join(df['Department'].unique())}")
    print(f"📍 Locations: {len(df['Location'].unique())} unique locations")
    print(f"💰 Total cost: ₹{df['Cost'].sum():,.2f}")
    
    return csv_filename

def login_and_get_token():
    """Login as admin and get session token"""
    print("\n🔐 Admin Login Process")
    print("=" * 40)
    
    email = input("Enter admin email: ").strip()
    
    # Simulate Firebase token (replace with actual Firebase integration)
    id_token = f"simulated_firebase_token_{email}"
    
    login_data = {'idToken': id_token}
    
    try:
        response = requests.post('http://127.0.0.1:5000/api/auth/login', json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            session_token = result.get('data', {}).get('session_token')
            user_info = result.get('data', {}).get('user')
            
            print(f"✅ Login successful!")
            print(f"👤 User: {user_info.get('name', 'N/A')} ({user_info.get('email')})")
            print(f"🔑 Role: {user_info.get('role')}")
            
            return session_token
        else:
            print(f"❌ Login failed: {response.json()}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def upload_csv_file(csv_filename, session_token):
    """Upload CSV file to the backend"""
    print(f"\n📤 Uploading CSV File: {csv_filename}")
    print("=" * 40)
    
    if not session_token:
        print("❌ No session token provided")
        return False
    
    headers = {
        'Authorization': f'Bearer {session_token}'
    }
    
    try:
        with open(csv_filename, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                'http://127.0.0.1:5000/api/upload/csv', 
                files=files, 
                headers=headers,
                timeout=30
            )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            data = result.get('data', {})
            
            print(f"✅ Upload successful!")
            print(f"📈 Records added: {data.get('success_count', 0)}")
            print(f"❌ Errors: {data.get('error_count', 0)}")
            
            if data.get('errors'):
                print("\n⚠️  Error details:")
                for error in data['errors'][:5]:  # Show first 5 errors
                    print(f"   • {error}")
            
            return True
        else:
            try:
                error_data = response.json()
                print(f"❌ Upload failed: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"❌ Upload failed: HTTP {response.status_code}")
            return False
            
    except FileNotFoundError:
        print(f"❌ File not found: {csv_filename}")
        return False
    except requests.exceptions.Timeout:
        print("❌ Upload timeout - file might be too large")
        return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def verify_upload(session_token):
    """Verify that the data was uploaded correctly"""
    print(f"\n🔍 Verifying Upload")
    print("=" * 40)
    
    headers = {
        'Authorization': f'Bearer {session_token}'
    }
    
    try:
        # Get resources count
        response = requests.get(
            'http://127.0.0.1:5000/api/resources?limit=100', 
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            data = result.get('data', {})
            
            print(f"✅ Verification successful!")
            print(f"📊 Total resources in system: {data.get('pagination', {}).get('total', 0)}")
            
            # Show sample of uploaded resources
            resources = data.get('resources', [])
            if resources:
                print(f"\n📋 Sample resources (showing first 3):")
                for i, resource in enumerate(resources[:3]):
                    print(f"   {i+1}. {resource.get('description')} - {resource.get('department')} - ₹{resource.get('cost', 0):,.2f}")
            
            return True
        else:
            print(f"❌ Verification failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

def main():
    """Main function to run the populate script"""
    print("🏫 Campus Assets Management - Data Population Script")
    print("=" * 60)
    
    # Step 1: Create sample CSV file
    csv_filename = create_sample_csv()
    
    # Step 2: Login and get session token
    session_token = login_and_get_token()
    
    if not session_token:
        print("\n❌ Cannot proceed without admin login")
        return
    
    # Step 3: Upload CSV file
    upload_success = upload_csv_file(csv_filename, session_token)
    
    if not upload_success:
        print("\n❌ Upload failed")
        return
    
    # Step 4: Verify upload
    verify_upload(session_token)
    
    print("\n🎉 Population script completed successfully!")
    print(f"📁 CSV file created: {csv_filename}")
    print("🔧 You can now test other features with this sample data")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Script interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
