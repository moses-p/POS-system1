import os
import shutil
import subprocess
from pathlib import Path

def clean_build_dirs():
    """Clean build and dist directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    # Clean .pyc files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))

def create_dist_package():
    """Create distribution package"""
    print("Creating distribution package...")
    
    # Create dist directory
    os.makedirs('dist', exist_ok=True)
    
    # Files to include
    files_to_include = [
        'app.py',
        'requirements.txt',
        'setup.py',
        'init_db.py',
        'README.md',
        'LICENSE',
        '.env.example',
        'USER_GUIDE.md',
        'INSTALLATION.md'
    ]
    
    # Directories to include
    dirs_to_include = [
        'templates',
        'static',
        'migrations'
    ]
    
    # Copy files
    for file in files_to_include:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join('dist', file))
    
    # Copy directories
    for dir_name in dirs_to_include:
        if os.path.exists(dir_name):
            shutil.copytree(dir_name, os.path.join('dist', dir_name))
    
    # Create .gitignore
    with open(os.path.join('dist', '.gitignore'), 'w') as f:
        f.write("""# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment variables
.env

# Database
*.db
*.sqlite3

# Logs
*.log

# OS
.DS_Store
Thumbs.db
""")

def create_zip_package():
    """Create zip package of the distribution"""
    print("Creating zip package...")
    shutil.make_archive('pos_system', 'zip', 'dist')
    print("Created pos_system.zip")

def main():
    """Main function to build distribution"""
    print("Starting distribution build...")
    
    # Clean build directories
    clean_build_dirs()
    
    # Create distribution package
    create_dist_package()
    
    # Create zip package
    create_zip_package()
    
    print("\nDistribution build completed!")
    print("Distribution package is available in the 'dist' directory")
    print("Zip package is available as 'pos_system.zip'")

if __name__ == '__main__':
    main() 