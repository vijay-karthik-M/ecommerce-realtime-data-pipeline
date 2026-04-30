#!/usr/bin/env python3
"""
Create admin user in Airflow 3.1.8 using Flask-AppBuilder ORM
"""

from airflow.www.app import create_app
from sqlalchemy.orm import sessionmaker

try:
    print("🔧 Creating Airflow app context...")
    app = create_app()
    
    with app.app_context():
        print("🔐 Accessing security manager...")
        sm = app.security_manager
        
        print("🔍 Checking for existing admin user...")
        user = sm.find_user(username='admin')
        
        if not user:
            print("👤 Creating new admin user...")
            sm.add_user(
                username='admin',
                first_name='Admin',
                last_name='User',
                email='admin@example.com',
                password='admin',
                role=sm.find_role('Admin')
            )
            print("✅ SUCCESS: Admin user created!")
            print("\n📋 Login Credentials:")
            print("   └─ Username: admin")
            print("   └─ Password: admin")
            print("\n🌐 Access Airflow UI: http://localhost:8080/")
        else:
            print("👤 Admin user already exists, updating password...")
            sm.update_user(
                user,
                password='admin'
            )
            print("✅ SUCCESS: Admin user password updated!")
            print("\n📋 Login Credentials:")
            print("   └─ Username: admin")
            print("   └─ Password: admin")
            print("\n🌐 Access Airflow UI: http://localhost:8080/")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
