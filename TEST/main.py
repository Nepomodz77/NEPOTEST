#!/usr/bin/python3
"""
Website Load Tester with Client-Side Firebase Auth
Complete Flask Backend
"""

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import requests
import time
import concurrent.futures
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a random string!

# Configuration defaults
DEFAULT_MAX_WORKERS = 50
DEFAULT_REQUESTS_PER_WORKER = 10
DEFAULT_TIMEOUT = 3

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # In production, verify the Firebase ID token here
        # For this demo, we'll just trust the client-side auth
        session['logged_in'] = True
        return jsonify({'status': 'success'})
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Main application routes
@app.route('/')
@login_required
def home():
    return render_template('index.html')

# Load testing functionality
def send_request(url, timeout):
    """Sends one GET request to the URL"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code
    except requests.RequestException as e:
        return str(e)

@app.route('/api/loadtest', methods=['POST'])
@login_required
def load_test():
    """API endpoint for load testing"""
    data = request.json
    
    if not data or 'url' not in data:
        return jsonify({"error": "URL is required"}), 400
    
    url = data['url']
    max_workers = int(data.get('workers', DEFAULT_MAX_WORKERS))
    requests_per_worker = int(data.get('requests_per_worker', DEFAULT_REQUESTS_PER_WORKER))
    timeout = int(data.get('timeout', DEFAULT_TIMEOUT))
    
    if max_workers <= 0 or requests_per_worker <= 0:
        return jsonify({"error": "Workers and requests must be positive integers"}), 400
    
    total_requests = max_workers * requests_per_worker
    
    start_time = time.time()
    
    results = {
        'total_requests': total_requests,
        'success': 0,
        'failed': 0,
        'status_codes': {},
        'errors': [],
        'start_time': start_time,
        'duration': 0
    }
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for _ in range(total_requests):
            futures.append(executor.submit(send_request, url, timeout))
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            
            if isinstance(result, int):  # Status code
                if result == 200:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                
                if result in results['status_codes']:
                    results['status_codes'][result] += 1
                else:
                    results['status_codes'][result] = 1
            else:  # Error message
                results['failed'] += 1
                results['errors'].append(result)
    
    results['duration'] = time.time() - start_time
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)