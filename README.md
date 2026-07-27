# COACH_PROJECT

This is a Django REST Framework (DRF) project initialized using `django-shortcuts`.

## Project Setup

### 1. Prerequisites
Ensure you have Python 3.8+ installed.

### 2. Environment Activation
Activate the virtual environment that was automatically created:

**On Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

### 3. Run Development Server
Start the Django development server:
```bash
python manage.py runserver
```
The server will start at `http://127.0.0.1:8000/`.

## Creating a Superuser
To access the Django Admin panel at `/admin/`, create a superuser:
```bash
python manage.py createsuperuser
```
