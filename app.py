from flask import Flask, request, jsonify, render_template_string, abort
import subprocess
import os
import uuid
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
import logging
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
download_dir = "/downloads"
status_file = "/downloads/status.json"
download_status = {}
executor = ThreadPoolExecutor(max_workers=4)
status_lock = threading.Lock()

# Video resolution options
RESOLUTION_OPTIONS = {
    "low": "240",
    "medium": "480",
    "high": "720",
    "hd": "1080",
    "best": "best"
}
DEFAULT_RESOLUTION = "medium"  # 480p by default

status_emojis = {
    'in progress': '⏳',
    'Downloaded': '✅',
    'Error': '❌',
    'Stderr': '⚠️'
}

# Initialize status from file if exists
def load_status_from_file():
    global download_status
    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                download_status = json.load(f)
                logger.info(f"Loaded {len(download_status)} download records from status file")
    except Exception as e:
        logger.error(f"Error loading status file: {e}")
        download_status = {}

# Save status to file
def save_status_to_file():
    try:
        with open(status_file, 'w') as f:
            json.dump(download_status, f, default=str)
    except Exception as e:
        logger.error(f"Error saving status file: {e}")

# Load status at startup
load_status_from_file()

@app.route('/')
def hello_world():
    return 'Hello World!'

def fetch_title(download_id, url):
    info_command = f"yt-dlp --get-title {url}"
    logger.info(f"Fetching title for ID: {download_id} with command: {info_command}")
    
    info_process = subprocess.Popen(info_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = info_process.communicate()

    with status_lock:
        if info_process.returncode != 0:
            download_status[download_id]['status'] = f"Error: {stderr}"
            download_status[download_id]['title'] = ''
            download_status[download_id]['filePath'] = ''
            download_status[download_id]['errored'] = datetime.now()
            
            logger.error(f"Error fetching title for ID: {download_id}: {stderr}")
            save_status_to_file()
            return

        download_status[download_id]['title'] = stdout.strip()
        save_status_to_file()
        
    download_video(download_id, url, download_status[download_id]['resolution'])

def download_video(download_id, url, resolution):
    with status_lock:
        title = download_status[download_id]['title']
        
    # Determine resolution parameter
    res_value = RESOLUTION_OPTIONS.get(resolution, RESOLUTION_OPTIONS[DEFAULT_RESOLUTION])
    
    # Build download command based on resolution
    if res_value == "best":
        download_command = f"yt-dlp -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' -o \"{download_dir}/%(title)s.%(ext)s\" {url}"
    else:
        download_command = f"yt-dlp -S \"+res:{res_value},codec,br\" -o \"{download_dir}/%(title)s.%(ext)s\" {url}"
    
    logger.info(f"Downloading video ID: {download_id} with resolution: {resolution} ({res_value})")
    logger.info(f"Command: {download_command}")
    
    download_process = subprocess.Popen(download_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = download_process.communicate()

    with status_lock:
        if download_process.returncode != 0:
            download_status[download_id]['errored'] = datetime.now()
            download_status[download_id]['status'] = f"Error: {stderr}"
            logger.error(f"Error downloading video for ID: {download_id}: {stderr}")
        else:
            download_status[download_id]['status'] = 'Downloaded'
            download_status[download_id]['ended'] = datetime.now()
            
            # Try to find the actual file path
            potential_extensions = ['.mp4', '.webm', '.mkv']
            file_path = None
            sanitized_title = ''.join(c if c.isalnum() or c in ' .-_' else '_' for c in title)
            
            for ext in potential_extensions:
                test_path = os.path.join(download_dir, f"{sanitized_title}{ext}")
                if os.path.exists(test_path):
                    file_path = test_path
                    break
            
            if file_path:
                download_status[download_id]['filePath'] = file_path
            else:
                # Fallback to assumed path
                download_status[download_id]['filePath'] = os.path.join(download_dir, f"{title}.mp4")
                
            logger.info(f"Completed download for ID: {download_id}")
        
        save_status_to_file()

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'error': 'Missing URL parameter'}), 400
            
        url = data.get('url')
        resolution = data.get('resolution', DEFAULT_RESOLUTION)
        
        # Validate resolution
        if resolution not in RESOLUTION_OPTIONS:
            resolution = DEFAULT_RESOLUTION
            
        download_id = str(uuid.uuid4())
        
        with status_lock:
            download_status[download_id] = {
                'status': 'in progress',
                'title': '',
                'filePath': '',
                'started': datetime.now(),
                'ended': None,
                'errored': None,
                'resolution': resolution,
                'url': url
            }
            save_status_to_file()
            
        logger.info(f"Initialized download for ID: {download_id}, URL: {url}, Resolution: {resolution}")

        executor.submit(fetch_title, download_id, url)
        return jsonify({'downloadId': download_id, 'message': 'Download started', 'resolution': resolution})
        
    except Exception as e:
        logger.error(f"Error in download endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/statusPage')
def status_page():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Download Status</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 20px; }
            h1 { color: #333; }
            ul { list-style-type: none; padding: 0; }
            li { padding: 15px; margin-bottom: 10px; border-radius: 5px; background-color: #f8f9fa; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .controls { margin-bottom: 20px; }
            button { background-color: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
            button.danger { background-color: #dc3545; }
            .empty-message { color: #6c757d; font-style: italic; }
            .status-in-progress { color: #fd7e14; }
            .status-downloaded { color: #28a745; }
            .status-error { color: #dc3545; }
        </style>
    </head>
    <body>
        <h1>Download Status</h1>
        
        <div class="controls">
            <button onclick="refreshPage()">Refresh</button>
            <button class="danger" onclick="if(confirm('Are you sure you want to clear all download history?')) clearHistory()">Clear History</button>
        </div>
        
        <div id="status-container">
    '''
    
    with status_lock:
        if not download_status:
            html += '<p class="empty-message">No downloads in history.</p>'
        else:
            html += '<ul>'
            for download_id, status in download_status.items():
                status_text = status['status']
                status_class = ""
                
                if status_text.startswith('in progress'):
                    status_class = "status-in-progress"
                elif status_text == 'Downloaded':
                    status_class = "status-downloaded"
                elif status_text.startswith('Error'):
                    status_class = "status-error"
                
                emoji = status_emojis.get(status_text.split(':')[0], '❓')
                resolution = status.get('resolution', DEFAULT_RESOLUTION)
                title = status.get('title', 'Unknown')
                
                html += f'''
                <li>
                    <strong>{emoji} {title}</strong><br>
                    Status: <span class="{status_class}">{status_text}</span><br>
                    Resolution: {resolution}<br>
                    Started: {status.get('started', 'Unknown')}
                </li>
                '''
            html += '</ul>'

    html += '''
        </div>
        
        <script>
            function refreshPage() {
                window.location.reload();
            }
            
            function clearHistory() {
                fetch('/clear-history', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.reload();
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(error => {
                    alert('Error clearing history: ' + error);
                });
            }
        </script>
    </body>
    </html>
    '''
    return html

@app.route('/status')
def status():
    with status_lock:
        return jsonify(list(download_status.values()))

@app.route('/clear-history', methods=['POST'])
def clear_history():
    try:
        with status_lock:
            global download_status
            download_status = {}
            save_status_to_file()
            logger.info("Download history cleared")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clean-downloads', methods=['POST'])
def clean_downloads():
    """Removes all downloaded files but keeps the history"""
    try:
        count = 0
        # Only remove files, not the directory itself
        for filename in os.listdir(download_dir):
            file_path = os.path.join(download_dir, filename)
            # Skip the status file
            if file_path == status_file:
                continue
                
            if os.path.isfile(file_path):
                os.remove(file_path)
                count += 1
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                count += 1
                
        logger.info(f"Cleaned {count} files/directories from download directory")
        return jsonify({'success': True, 'message': f'Removed {count} files'})
    except Exception as e:
        logger.error(f"Error cleaning downloads: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/resolutions', methods=['GET'])
def get_resolutions():
    """Returns available resolution options"""
    return jsonify({
        'default': DEFAULT_RESOLUTION,
        'options': list(RESOLUTION_OPTIONS.keys())
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    # Make sure download directory exists
    os.makedirs(download_dir, exist_ok=True)
    logger.info(f"Server starting on port 3000, downloads will be stored in {download_dir}")
    app.run(host='0.0.0.0', port=3000)