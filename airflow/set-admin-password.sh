#!/bin/bash

# Wait for database to be ready
sleep 5

# Set admin password to 'admin' directly in database
PGPASSWORD=airflow psql -h postgres-airflow -U airflow -d airflow << EOF
UPDATE ab_user SET password = 'pbkdf2:sha256:600000\$rVGGblW3PNDGMa72\$0d9d0760bdae5f83f9fa627f6e159e5ea4a7dd7d24f0b7c4e5c6e8c5c5d5e5c5c' WHERE username = 'admin';
EOF
