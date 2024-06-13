#!/bin/sh

# Wait for the database to be ready
./wait-for-it.sh db:3306 --timeout=30 --strict -- echo "Database is up"

# Apply database migrations
python manage.py makemigrations
python manage.py migrate 

# Collect static files (if necessary)
python manage.py collectstatic --noinput

# Start qcluster in the background - Used to send emails asynchonously
python manage.py qcluster &

# Start the server
exec "$@"