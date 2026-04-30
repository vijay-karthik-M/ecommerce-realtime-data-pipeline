#!/usr/bin/env python3
"""
Create an Airflow user for Airflow 3.x
"""
import sys

try:
    # Try multiple import paths for compatibility
    try:
        from airflow.models import User
    except ImportError:
        try:
            from airflow.auth.models import User
        except ImportError:
            try:
                from airflow.security.models import User
            except ImportError:
                # For Airflow 3.x, User might be in datalayer
                from sqlalchemy import Column, String, Boolean, Integer
                from sqlalchemy.ext.declarative import declarative_base
                from airflow import settings
                
                Base = declarative_base()
                
                class User(Base):
                    __tablename__ = 'ab_user'
                    id = Column(Integer, primary_key=True)
                    username = Column(String(250), unique=True)
                    email = Column(String(250))
                    is_active = Column(Boolean, default=True)
                    is_superuser = Column(Boolean, default=False)
                    password = Column(String(255))
                    
                    def set_password(self, password):
                        try:
                            from werkzeug.security import generate_password_hash
                            self.password = generate_password_hash(password)
                        except:
                            self.password = password

    from airflow import settings
    from sqlalchemy.orm import sessionmaker
    
    # Create session
    Session = sessionmaker(bind=settings.engine)
    session = Session()
    
    # Create user
    user = User(
        username='admin',
        email='vijaykarthik0102@gmail.com',
        is_active=True,
        is_superuser=True
    )
    user.set_password('admin')
    
    session.add(user)
    session.commit()
    session.close()
    
    print("✓ User 'admin' created successfully!")
    print("  Username: admin")
    print("  Email: vijaykarthik0102@gmail.com")
    print("  Role: Admin (Superuser)")
    sys.exit(0)
    
except Exception as e:
    print(f"✗ Error creating user: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
