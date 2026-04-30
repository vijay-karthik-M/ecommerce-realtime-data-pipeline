#!/bin/bash
set -e

echo "🚀 Initializing Airflow..."

# Run database migrations
echo "📊 Running database migrations..."
airflow db migrate

# Create admin user using Flask-AppBuilder
echo "👤 Creating admin user..."
python3 << EOF
from airflow.www.app import create_app
from airflow.www.security import AppBuilderAirflowSecurityManager

app = create_app()
app.app_context().push()

sm = app.security_manager
user = sm.find_user(username='admin')

if not user:
    sm.add_user(
        username='admin',
        first_name='Admin',
        last_name='User',
        email='admin@example.com',
        password='admin',
        role=sm.find_role('Admin')
    )
    print("✅ Admin user created successfully!")
else:
    sm.update_user(user, password='admin')
    print("✅ Admin user password updated!")
EOF

echo "✅ Airflow initialization complete!"
