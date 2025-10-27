from flask import Flask, render_template, request, jsonify, Response
import paramiko
import os
from datetime import datetime
import re
from dotenv import load_dotenv
import threading
import queue

load_dotenv()

app = Flask(__name__)

# Server configuration
SERVERS = {
    '200a': {
        'hostname': '200a.friends.com',
        'username': os.getenv('SERVER200A_USER', 'your_username'),
        'password': os.getenv('SERVER200A_PASSWORD', 'your_password'),
        'key_file': os.getenv('SERVER200A_KEYFILE', None)
    },
    '201a': {
        'hostname': '201a.friends.com',
        'username': os.getenv('SERVER201A_USER', 'your_username'),
        'password': os.getenv('SERVER201A_PASSWORD', 'your_password'),
        'key_file': os.getenv('SERVER201A_KEYFILE', None)
    }
}

# Common log file locations
LOG_PATHS = [
    '/var/log/',
    '/opt/logs/',
    '/home/user/logs/',
    '/tmp/logs/'
]

def get_ssh_connection(server_key):
    """Establish SSH connection to server"""
    try:
        server_config = SERVERS[server_key]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if server_config['key_file']:
            ssh.connect(
                server_config['hostname'],
                username=server_config['username'],
                key_filename=server_config['key_file']
            )
        else:
            ssh.connect(
                server_config['hostname'],
                username=server_config['username'],
                password=server_config['password']
            )
        return ssh
    except Exception as e:
        print(f"SSH Connection Error: {e}")
        return None

def discover_log_files(server_key, path_filter=""):
    """Discover log files on the server"""
    ssh = get_ssh_connection(server_key)
    if not ssh:
        return []
    
    log_files = []
    try:
        for log_path in LOG_PATHS:
            # Find files with common log extensions
            command = f"find {log_path} -type f -name '*.log' -o -name '*.txt' -o -name '*.out' 2>/dev/null | head -50"
            if path_filter:
                command = f"find {log_path} -type f -name '*{path_filter}*' 2>/dev/null | head -50"
            
            stdin, stdout, stderr = ssh.exec_command(command)
            files = stdout.read().decode().splitlines()
            
            for file_path in files:
                if file_path:  # Ensure path is not empty
                    log_files.append({
                        'path': file_path,
                        'name': os.path.basename(file_path)
                    })
        
        # Remove duplicates
        seen = set()
        unique_logs = []
        for log in log_files:
            if log['path'] not in seen:
                seen.add(log['path'])
                unique_logs.append(log)
        
        return unique_logs
        
    except Exception as e:
        print(f"Error discovering log files: {e}")
        return []
    finally:
        ssh.close()

def search_in_file(server_key, file_path, search_text, max_lines=1000):
    """Search for text in a log file"""
    ssh = get_ssh_connection(server_key)
    if not ssh:
        return []
    
    try:
        # Use grep to search for the text
        command = f"grep -n -i '{search_text}' '{file_path}' | head -{max_lines}"
        stdin, stdout, stderr = ssh.exec_command(command)
        results = stdout.read().decode().splitlines()
        
        formatted_results = []
        for result in results:
            if ':' in result:
                line_num, content = result.split(':', 1)
                formatted_results.append({
                    'line_number': int(line_num),
                    'content': content.strip(),
                    'file_path': file_path
                })
        
        return formatted_results
        
    except Exception as e:
        print(f"Error searching file: {e}")
        return []
    finally:
        ssh.close()

def tail_file(server_key, file_path, lines=100):
    """Get last n lines of a file"""
    ssh = get_ssh_connection(server_key)
    if not ssh:
        return []
    
    try:
        command = f"tail -n {lines} '{file_path}'"
        stdin, stdout, stderr = ssh.exec_command(command)
        content = stdout.read().decode()
        return content.splitlines()
    except Exception as e:
        print(f"Error tailing file: {e}")
        return []
    finally:
        ssh.close()

@app.route('/')
def index():
    """Main page with search form"""
    return render_template('index.html', servers=SERVERS.keys())

@app.route('/get_log_files')
def get_log_files():
    """API endpoint to get log files for a server"""
    server_key = request.args.get('server')
    path_filter = request.args.get('filter', '')
    
    if server_key not in SERVERS:
        return jsonify({'error': 'Invalid server'}), 400
    
    log_files = discover_log_files(server_key, path_filter)
    return jsonify({'log_files': log_files})

@app.route('/search', methods=['POST'])
def search_logs():
    """Search logs endpoint"""
    server_key = request.form.get('server')
    file_path = request.form.get('file_path')
    search_text = request.form.get('search_text')
    max_results = int(request.form.get('max_results', 100))
    
    if not all([server_key, file_path, search_text]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if server_key not in SERVERS:
        return jsonify({'error': 'Invalid server'}), 400
    
    results = search_in_file(server_key, file_path, search_text, max_results)
    
    return render_template('search_results.html', 
                         results=results,
                         search_text=search_text,
                         file_path=file_path,
                         server=server_key)

@app.route('/tail')
def tail_logs():
    """Tail logs endpoint"""
    server_key = request.args.get('server')
    file_path = request.args.get('file_path')
    lines = int(request.args.get('lines', 100))
    
    if not all([server_key, file_path]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if server_key not in SERVERS:
        return jsonify({'error': 'Invalid server'}), 400
    
    content = tail_file(server_key, file_path, lines)
    return jsonify({'content': content, 'file_path': file_path})

@app.route('/live_tail')
def live_tail():
    """Live tail endpoint (SSE)"""
    server_key = request.args.get('server')
    file_path = request.args.get('file_path')
    
    def generate():
        ssh = get_ssh_connection(server_key)
        if not ssh:
            yield f"data: Error connecting to server\n\n"
            return
        
        try:
            # Use tail -f for live following
            command = f"tail -f '{file_path}'"
            stdin, stdout, stderr = ssh.exec_command(command)
            
            for line in iter(stdout.readline, ""):
                yield f"data: {line}\n\n"
                
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
        finally:
            ssh.close()
    
    return Response(generate(), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
