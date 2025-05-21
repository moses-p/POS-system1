import os
import sys
import shutil
import subprocess

def build_executable():
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

    # Clean up previous build
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('POS_system.spec'):
        os.remove('POS_system.spec')

    # Create necessary directories
    for dir_name in ['instance', 'logs']:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

    # Build command with necessary options
    cmd = [
        'pyinstaller',
        '--name=POS_system',
        '--onefile',
        '--windowed',
        '--add-data=templates;templates',
        '--add-data=static;static',
        '--add-data=instance;instance',
        '--add-data=logs;logs',
        '--icon=static/favicon.ico',
        '--hidden-import=engineio.async_drivers.threading',
        '--hidden-import=flask_socketio',
        '--hidden-import=sqlalchemy',
        '--hidden-import=flask_sqlalchemy',
        '--hidden-import=flask_login',
        '--hidden-import=flask_mail',
        '--hidden-import=flask_wtf',
        '--hidden-import=email_validator',
        '--hidden-import=bcrypt',
        '--hidden-import=jinja2',
        '--hidden-import=werkzeug',
        '--hidden-import=click',
        '--hidden-import=itsdangerous',
        '--hidden-import=markupsafe',
        '--hidden-import=python-dateutil',
        '--hidden-import=python-engineio',
        '--hidden-import=python-socketio',
        'app.py'
    ]

    # Run PyInstaller
    subprocess.check_call(cmd)

    # Copy necessary files to dist
    for dir_name in ['instance', 'logs']:
        dist_dir = os.path.join('dist', dir_name)
        if not os.path.exists(dist_dir):
            os.makedirs(dist_dir)
        if dir_name == 'instance' and os.path.exists('instance/pos.db'):
            shutil.copy2('instance/pos.db', dist_dir)

    print("\nBuild completed successfully!")
    print("Executable can be found in the 'dist' folder")
    print("Logs will be written to the 'logs' directory")

if __name__ == '__main__':
    build_executable() 