# Create a Python virtual environment

python -m venv venv

# Activate the virtual environment

# or MacOS

source venv/bin/activate

# to exit

deactivate

# Install the required packages from requirements.txt

pip install -r requirements.txt

# Update the database configurations
mysite -> settings -> dev.py

# scroll to the bottom and input your local database configuration

# Start the app - (if using a local database run the commands below)

python manage.py migrate\
python manage.py createsuperuser\
python manage.py bootstrap_cms_pages

python manage.py runserver

# CSS + JS files can be found in the folder "assets"
