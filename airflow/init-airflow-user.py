#!/usr/bin/env python3
"""Initialize Airflow admin user with simple password"""
import os
from airflow.sec.models import User
from airflow import settings

# Create admin user
session = settings.Session()
user = session.query(User).filter(User.username == 'admin').first()

if not user:
    user = User(
        username='admin',
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        is_active=True,
        is_superuser=True
    )
    user.set_password('admin')
    session.add(user)
    session.commit()
    print("Admin user created with password: admin")
else:
    print("Admin user already exists")
