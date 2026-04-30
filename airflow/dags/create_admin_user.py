#!/usr/bin/env python3
"""
Create admin user in Airflow 3.1.8 using direct database ORM
"""

import os
from airflow import settings
from airflow.api_fastapi import common
from sqlalchemy.orm import sessionmaker
from airflow.models import User

try:
    print("🔧 Setting up database session...")
    Session = sessionmaker(bind=settings.engine)
    session = Session()
    
    print("🔍 Checking for existing admin user...")
    user = session.query(User).filter(User.username == 'admin').first()
    
    if not user:
        print("👤 Creating new admin user...")
        new_user = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            is_superuser=True,
            is_active=True
        )
        new_user.set_password('admin')
        session.add(new_user)
        session.commit()
        print("✅ SUCCESS: Admin user created!")
    else:
        print("👤 Admin user already exists, updating password...")
        user.set_password('admin')
        user.is_active = True
        user.is_superuser = True
        session.merge(user)
        session.commit()
        print("✅ SUCCESS: Admin user password updated!")
    
    session.close()
    
    print("\n📋 Login Credentials:")
    print("   └─ Username: admin")
    print("   └─ Password: admin")
    print("\n🌐 Access Airflow UI: http://localhost:8080/")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
