from flask import Flask, request, jsonify, render_template_string
import subprocess
import os
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

app = Flask(__name__)
download_dir = "/downloads"
download_status = {}
executor = ThreadPoolExecutor(max_workers=4)  # Increase the number of threads for better concurrency
status_lock = threading.Lock()

status_emojis = {
    'in progress': '⏳',
    'Downloaded': '✅',
    'Error': '❌',
    'Stderr': '⚠️'
}

@app.route('/')
def hello_world():
    return 'Hello World!'

def fetch_title(download_id, url):
    info_command = f"yt-dlp --get-title {url}"
    info_process = subprocess.Popen(info_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = info_process.communicate()

    with status_lock:
        if info_process.returncode != 0:
            download_status[download_id] = {
                'status': f"Error: {stderr}",
                'title': '',
                'filePath': ''
            }
            print(f"Error fetching title for ID: {download_id}")
            return

        download_status[download_id]['title'] = stdout.strip()
    download_video(download_id, url)

def download_video(download_id, url):
    with status_lock:
        title = download_status[download_id]['title']
    download_command = f"yt-dlp -S \"+res:480,codec,br\" -o \"{download_dir}/%(title)s.%(ext)s\" {url}"
    download_process = subprocess.Popen(download_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = download_process.communicate()

    with status_lock:
        if download_process.returncode != 0:
            download_status[download_id]['errored'] = datetime.now()
            download_status[download_id]['status'] = f"Error: {stderr}"
            print(f"Error downloading video for ID: {download_id}")
            return

        download_status[download_id]['status'] = 'Downloaded'
        download_status[download_id]['ended'] = datetime.now()
        download_status[download_id]['filePath'] = os.path.join(download_dir, f"{download_status[download_id]['title']}.mp4")

    print(f"Completed download for ID: {download_id}")

@app.route('/download', methods=['POST'])
def download():
    url = request.json.get('url')
    download_id = str(uuid.uuid4())
    
    with status_lock:
        download_status[download_id] = {
            'status': 'in progress',
            'title': '',
            'filePath': '',
            'started': datetime.now(),
            'ended': None,
            'errored': None
        }
    print(f"Initialized download for ID: {download_id}")

    executor.submit(fetch_title, download_id, url)
    return jsonify({'downloadId': download_id, 'message': 'Download started'})

@app.route('/statusPage')
def status_page():
    html = '<html><head><title>Download Status</title></head><body>'
    html += '<h1>Download Status</h1><ul>'

    with status_lock:
        for download_id, status in download_status.items():
            emoji = status_emojis.get(status['status'].split(':')[0], '❓')
            html += f"<li>{emoji} <strong>{status['title']}</strong>: {status['status']}</li>"

    html += '</ul></body></html>'
    return render_template_string(html)

@app.route('/status')
def status():
    with status_lock:
        return jsonify(list(download_status.values()))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
