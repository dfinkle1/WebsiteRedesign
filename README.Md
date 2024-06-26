# Create a Python virtual environment

python -m venv venv

# Activate the virtual environment

# On Windows

myenv\Scripts\activate

# or MacOS

source venv/bin/activate

# to exit

deactivate

# Install the required packages from requirements.txt

pip install -r requirements.txt

# Start the app

python manage.py runserver

##Code Structure

```bash
< PROJECT ROOT >
   |
   |-- mysite/
   |    -- settings.py                  # Project Configuration
   |    -- urls.py                      # Project Routing
   |
   |-- apps/
   |    |-- core/
   |        |-- urls.py                      # app Routing
   |        |-- views.py                     # APP Views
   |        |-- urls.py                      # APP Routing
   |        |-- models.py                    # APP Models
   |    |-- workshops/                   # inactive
   |-- templates/
   |    |-- base.html
   |    |-- navbar/                 #static template directory
   |
   |-- static/
   |    |-- css
   |    |-- js
   |    |-- images
   |-- requirements.txt                  # Project Dependencies
   |
   |-- manage.py                         # Start the app - Django default start script
   |
   |-- ************************************************************************
```

# Update the database configurations in mysite -> settings.py

# Find the DATABASES section and update the USER field with your name/user

DATABASES = {
"default": {
"ENGINE": "django.db.backends.postgresql",
"NAME": "#databaseName#",
"USER": "#databaseUser#", # Replace #databaseUser# with your name/user
"PASSWORD": "",
"HOST": "localhost",
"PORT": "",
}
}

# I may need to send .sql files for this, but it is not the main concern at the moment
