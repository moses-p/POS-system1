import os
import shutil
import subprocess
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def clean_build():
    """Clean build artifacts and cache"""
    dirs_to_clean = ['build', 'dist', '__pycache__', '.pytest_cache']
    files_to_clean = ['*.pyc', '*.pyo', '*.pyd', '*.spec']
    
    # Clean directories
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            logger.info(f"Removing directory: {dir_name}")
            shutil.rmtree(dir_name)
    
    # Clean files
    for pattern in files_to_clean:
        for file in os.listdir('.'):
            if file.endswith(pattern[1:]):  # Remove * from pattern
                logger.info(f"Removing file: {file}")
                os.remove(file)
    
    # Clean instance directory
    if os.path.exists('instance'):
        logger.info("Cleaning instance directory")
        shutil.rmtree('instance')
    # Always create a fresh instance directory
    os.makedirs('instance', exist_ok=True)

def rebuild():
    """Rebuild the application"""
    try:
        # Clean first
        clean_build()
        
        # Install/upgrade required packages
        logger.info("Installing/upgrading required packages...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', '-r', 'requirements.txt'], check=True)
        
        # Run PyInstaller
        logger.info("Building with PyInstaller...")
        subprocess.run([
            'pyinstaller',
            '--name=POS_System',
            '--onefile',
            '--windowed',
            '--add-data=templates;templates',
            '--add-data=static;static',
            '--add-data=instance;instance',
            '--icon=static/favicon.ico',
            '--hidden-import=eventlet.hubs.epolls',
            '--hidden-import=eventlet.hubs.selects',
            '--hidden-import=eventlet.hubs.polls',
            '--hidden-import=eventlet.hubs.kqueue',
            '--hidden-import=dns',
            '--hidden-import=dns.rdatatype',
            '--hidden-import=dns.rdtypes',
            '--hidden-import=dns.rdtypes.ANY',
            '--hidden-import=dns.rdtypes.IN',
            '--hidden-import=dns.rdtypes.CH',
            '--hidden-import=dns.rdtypes.dnskeybase',
            '--hidden-import=dns.asyncbackend',
            '--hidden-import=dns.dnssec',
            '--hidden-import=dns.e164',
            '--hidden-import=dns.namedict',
            '--hidden-import=dns.tsigkeyring',
            '--hidden-import=dns.versioned',
            'pos_launcher.py'
        ], check=True)
        
        logger.info("Build completed successfully!")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    rebuild() 