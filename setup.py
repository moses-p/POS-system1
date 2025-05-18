import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"Python version {sys.version_info.major}.{sys.version_info.minor} detected")

def create_virtual_env():
    """Create a virtual environment"""
    try:
        if not os.path.exists('venv'):
            print("Creating virtual environment...")
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
            print("Virtual environment created successfully")
        else:
            print("Virtual environment already exists")
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment: {str(e)}")
        sys.exit(1)

def install_requirements():
    """Install required packages"""
    try:
        print("Installing requirements...")
        if os.name == 'nt':  # Windows
            pip_path = os.path.join('venv', 'Scripts', 'pip')
        else:  # Unix/Linux/MacOS
            pip_path = os.path.join('venv', 'bin', 'pip')
        
        # Upgrade pip first
        subprocess.run([pip_path, 'install', '--upgrade', 'pip'], check=True)
        
        # Install requirements
        subprocess.run([pip_path, 'install', '-r', 'requirements.txt'], check=True)
        print("Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {str(e)}")
        sys.exit(1)

def create_env_file():
    """Create .env file from .env.example if it doesn't exist"""
    try:
        if not os.path.exists('.env'):
            if os.path.exists('.env.example'):
                shutil.copy('.env.example', '.env')
                print("Created .env file from .env.example")
                print("Please update the .env file with your configuration")
            else:
                print("Warning: .env.example not found")
                print("Please create a .env file with your configuration")
        else:
            print(".env file already exists")
    except Exception as e:
        print(f"Error creating .env file: {str(e)}")
        sys.exit(1)

def initialize_database():
    """Initialize the database"""
    try:
        print("Initializing database...")
        if os.name == 'nt':  # Windows
            python_path = os.path.join('venv', 'Scripts', 'python')
        else:  # Unix/Linux/MacOS
            python_path = os.path.join('venv', 'bin', 'python')
        
        # Initialize database without creating admin
        subprocess.run([python_path, 'init_db.py'], check=True)
        
        # Ask if user wants to create initial admin
        create_admin = input("\nDo you want to create the initial admin user? (y/n): ").lower().strip()
        if create_admin == 'y':
            subprocess.run([python_path, 'create_initial_admin.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error initializing database: {str(e)}")
        sys.exit(1)

def check_directories():
    """Check and create necessary directories"""
    try:
        directories = ['instance', 'logs', 'uploads']
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Created directory: {directory}")
    except Exception as e:
        print(f"Error creating directories: {str(e)}")
        sys.exit(1)

def main():
    """Main setup function"""
    print("Starting POS System setup...")
    
    # Check Python version
    check_python_version()
    
    # Create virtual environment
    create_virtual_env()
    
    # Install requirements
    install_requirements()
    
    # Create necessary directories
    check_directories()
    
    # Create .env file
    create_env_file()
    
    # Initialize database
    initialize_database()
    
    print("\nSetup completed successfully!")
    print("\nTo start the application:")
    if os.name == 'nt':  # Windows
        print("1. Activate virtual environment: venv\\Scripts\\activate")
        print("2. Run the application: python app.py")
    else:  # Unix/Linux/MacOS
        print("1. Activate virtual environment: source venv/bin/activate")
        print("2. Run the application: python app.py")
    
    print("\nDefault login credentials:")
    print("Admin - Username: admin, Password: admin123")
    print("Staff - Username: staff, Password: staff123")
    print("\nPlease change these passwords after first login!")

if __name__ == '__main__':
    main() 