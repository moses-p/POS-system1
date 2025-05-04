import os
import re
import shutil
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_ui_fixes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def backup_file(file_path):
    """Create a backup of a file"""
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        return False
    
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating backup of {file_path}: {str(e)}")
        return False

def check_and_improve_app_js():
    """
    Check and improve the stock refresh functionality in app.js.
    This handles the client-side logic for updating stock display.
    """
    file_path = 'static/js/app.js'
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Create a backup first
    if not backup_file(file_path):
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modifications = []
        
        # Check if the refreshStock function is properly implemented
        if 'function refreshStock(' in content:
            logger.info("Found refreshStock function in app.js")
            
            # Check for proper error handling in fetch requests
            if '.catch' in content and 'retry' in content:
                logger.info("refreshStock function has error handling with retry mechanism")
            else:
                logger.warning("refreshStock function may be missing proper error handling or retry mechanism")
                modifications.append("Add proper error handling and retry mechanism to refreshStock function")
            
            # Check for force cache-busting in fetch requests
            if 'cache: \'no-store\'' in content:
                logger.info("refreshStock function has cache-busting headers")
            else:
                logger.warning("refreshStock function may be missing cache-busting headers")
                modifications.append("Add cache-busting headers to refreshStock function")
            
            # If we need to make modifications to the refreshStock function
            if "Add cache-busting headers to refreshStock function" in modifications:
                # Add cache-busting to the fetch options
                new_content = re.sub(
                    r'fetch\(url,\s*\{\s*method:\s*\'GET\'',
                    'fetch(url, {\n                method: \'GET\',\n                cache: \'no-store\'',
                    content
                )
                
                # Add cache control headers if not already present
                if 'Cache-Control' not in content:
                    new_content = re.sub(
                        r'headers:\s*\{',
                        'headers: {\n                    \'Cache-Control\': \'no-cache, no-store, must-revalidate\',\n                    \'Pragma\': \'no-cache\',\n                    \'Expires\': \'0\',',
                        new_content
                    )
                
                # Save the modified content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                logger.info("Added cache-busting improvements to refreshStock function")
        else:
            logger.error("Could not find refreshStock function in app.js")
            return False
        
        # Check if updateProductStockUI function is properly implemented
        if 'function updateProductStockUI(' in content:
            logger.info("Found updateProductStockUI function in app.js")
            
            # Check if it properly updates all elements
            if 'stockElements.forEach(' in content:
                logger.info("updateProductStockUI iterates through all stock elements")
            else:
                logger.warning("updateProductStockUI may not be updating all elements correctly")
                modifications.append("Improve updateProductStockUI to update all stock elements")
        else:
            logger.error("Could not find updateProductStockUI function in app.js")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error checking/improving app.js: {str(e)}")
        return False

def fix_stock_refresh_in_templates():
    """
    Fix stock refresh in HTML templates by ensuring they properly call 
    refreshStock() when needed and have appropriate polling intervals.
    """
    templates_to_check = [
        'templates/index.html',
        'templates/inventory_management.html',
        'templates/in_store_sale.html',
        'templates/product_detail.html'
    ]
    
    for template_path in templates_to_check:
        if not os.path.exists(template_path):
            logger.warning(f"Template file not found: {template_path}")
            continue
        
        logger.info(f"Checking template: {template_path}")
        
        # Create a backup first
        if not backup_file(template_path):
            continue
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if the template calls refreshStock
            if 'refreshStock(' in content:
                logger.info(f"Template {template_path} calls refreshStock function")
                
                # Check if it has auto-refresh mechanism
                if 'setInterval' in content and 'refreshStock' in content:
                    logger.info(f"Template {template_path} has auto-refresh mechanism")
                else:
                    logger.warning(f"Template {template_path} may be missing auto-refresh mechanism")
                    
                    # Inject an auto-refresh mechanism if the file is index.html or inventory_management.html
                    if template_path.endswith('index.html') or template_path.endswith('inventory_management.html'):
                        # Find the document.addEventListener('DOMContentLoaded'... section
                        dom_loaded_match = re.search(r'document\.addEventListener\(\'DOMContentLoaded\',\s*function\(\)\s*\{', content)
                        
                        if dom_loaded_match:
                            # Insert setInterval code after the DOMContentLoaded event listener
                            modified_content = content[:dom_loaded_match.end()] + '\n' + \
                                '    // Auto-refresh stock information every 10 seconds\n' + \
                                '    setInterval(function() {\n' + \
                                '        if (typeof refreshStock === \'function\') {\n' + \
                                '            console.log(\'Auto-refreshing stock information...\');\n' + \
                                '            refreshStock();\n' + \
                                '        }\n' + \
                                '    }, 10000);\n' + \
                                '    \n' + \
                                '    // Initial stock refresh\n' + \
                                '    if (typeof refreshStock === \'function\') {\n' + \
                                '        console.log(\'Initial stock refresh...\');\n' + \
                                '        refreshStock();\n' + \
                                '    }\n' + \
                                content[dom_loaded_match.end():]
                            
                            # Save the modified content
                            with open(template_path, 'w', encoding='utf-8') as f:
                                f.write(modified_content)
                            logger.info(f"Added auto-refresh mechanism to {template_path}")
            else:
                logger.warning(f"Template {template_path} does not call refreshStock function")
            
        except Exception as e:
            logger.error(f"Error checking/improving template {template_path}: {str(e)}")
    
    return True

def ensure_force_refresh_button():
    """
    Add a force refresh button to relevant pages if not already present
    """
    templates_to_check = [
        'templates/index.html',
        'templates/product_detail.html',
        'templates/base.html'
    ]
    
    button_html = '''
    <button id="forceRefreshBtn" class="btn btn-sm btn-outline-secondary" onclick="refreshStock()">
        <i class="fas fa-sync-alt"></i> Refresh Stock
    </button>
    '''
    
    for template_path in templates_to_check:
        if not os.path.exists(template_path):
            logger.warning(f"Template file not found: {template_path}")
            continue
        
        # Skip if it's base.html and we're looking to add a specific button
        if template_path.endswith('base.html'):
            continue
        
        logger.info(f"Checking for refresh button in: {template_path}")
        
        # Create a backup first
        if not backup_file(template_path):
            continue
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if a force refresh button already exists
            if 'forceRefreshBtn' in content or 'Refresh Stock' in content:
                logger.info(f"Template {template_path} already has a refresh button")
            else:
                logger.info(f"Adding refresh button to {template_path}")
                
                # For index.html, add it to the top navbar/header area
                if template_path.endswith('index.html'):
                    # Find a suitable place to insert the button
                    container_match = re.search(r'<div class="container[^>]*>', content)
                    if container_match:
                        modified_content = content[:container_match.end()] + '\n' + \
                            '    <div class="d-flex justify-content-end mb-3">\n' + \
                            '        ' + button_html.strip() + '\n' + \
                            '    </div>' + \
                            content[container_match.end():]
                        
                        # Save the modified content
                        with open(template_path, 'w', encoding='utf-8') as f:
                            f.write(modified_content)
                        logger.info(f"Added refresh button to {template_path}")
        
        except Exception as e:
            logger.error(f"Error adding refresh button to {template_path}: {str(e)}")
    
    return True

def main():
    """Run all improvements for stock refresh functionality"""
    logger.info("Starting stock refresh functionality improvements...")
    
    # Check and improve app.js
    check_and_improve_app_js()
    
    # Fix stock refresh in templates
    fix_stock_refresh_in_templates()
    
    # Add force refresh buttons where needed
    ensure_force_refresh_button()
    
    logger.info("Stock refresh functionality improvements completed")

if __name__ == "__main__":
    main() 