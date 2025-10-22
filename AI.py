import re
import json
from datetime import datetime, timedelta

# --- AI Chat Feature ---
class LogAnalyzer:
    def __init__(self):
        self.patterns = {
            'error': r'(error|exception|failed|failure|crash|segfault)',
            'warning': r'(warning|warn|caution|attention)',
            'http_status': r'HTTP/\d\.\d"\s+(\d{3})',
            'timestamp': r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})|(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})',
            'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            'url': r'(GET|POST|PUT|DELETE)\s+([^\s]+)',
            'database': r'(database|sql|query|transaction|connection)',
            'memory': r'(memory|ram|oom|out of memory)',
            'disk': r'(disk|space|storage|full)',
            'performance': r'(slow|timeout|latency|performance|bottleneck)'
        }
    
    def analyze_log_patterns(self, log_content):
        """Analyze log content for common patterns"""
        analysis = {
            'errors': [],
            'warnings': [],
            'http_codes': {},
            'timestamps': [],
            'ips': [],
            'urls': [],
            'suggestions': []
        }
        
        lines = log_content.split('\n')
        
        for i, line in enumerate(lines[:1000]):  # Analyze first 1000 lines
            line = line.strip()
            if not line:
                continue
                
            # Check for errors
            if re.search(self.patterns['error'], line, re.IGNORECASE):
                analysis['errors'].append(f"Line {i+1}: {line[:100]}...")
            
            # Check for warnings
            if re.search(self.patterns['warning'], line, re.IGNORECASE):
                analysis['warnings'].append(f"Line {i+1}: {line[:100]}...")
            
            # Extract HTTP status codes
            http_match = re.search(self.patterns['http_status'], line)
            if http_match:
                status_code = http_match.group(1)
                analysis['http_codes'][status_code] = analysis['http_codes'].get(status_code, 0) + 1
            
            # Extract IP addresses
            ips = re.findall(self.patterns['ip_address'], line)
            analysis['ips'].extend(ips)
            
            # Extract URLs
            url_match = re.search(self.patterns['url'], line)
            if url_match:
                analysis['urls'].append(f"{url_match.group(1)} {url_match.group(2)}")
        
        # Generate suggestions based on findings
        analysis['suggestions'] = self.generate_suggestions(analysis)
        
        return analysis
    
    def generate_suggestions(self, analysis):
        """Generate intelligent suggestions based on log analysis"""
        suggestions = []
        
        if len(analysis['errors']) > 10:
            suggestions.append("High number of errors detected. Consider checking application configuration.")
        
        if '500' in analysis['http_codes'] and analysis['http_codes']['500'] > 5:
            suggestions.append("Multiple 500 Internal Server Errors detected. Check server-side code.")
        
        if '404' in analysis['http_codes'] and analysis['http_codes']['404'] > 10:
            suggestions.append("Many 404 Not Found errors. Verify URL routes and resource availability.")
        
        if len(analysis['warnings']) > 20:
            suggestions.append("Numerous warnings found. Review application logs for potential issues.")
        
        if any('memory' in error.lower() for error in analysis['errors']):
            suggestions.append("Memory-related issues detected. Check memory usage and allocation.")
        
        if any('database' in error.lower() for error in analysis['errors']):
            suggestions.append("Database errors found. Verify database connection and queries.")
        
        if not suggestions:
            suggestions.append("No critical issues detected in the analyzed log content.")
        
        return suggestions
    
    def process_query(self, query, log_content, log_filename):
        """Process user query and provide intelligent response"""
        query_lower = query.lower()
        
        # Common question patterns
        if any(word in query_lower for word in ['error', 'problem', 'issue', 'wrong']):
            analysis = self.analyze_log_patterns(log_content)
            return self.format_error_analysis(analysis, log_filename)
        
        elif any(word in query_lower for word in ['summary', 'overview', 'analyze']):
            analysis = self.analyze_log_patterns(log_content)
            return self.format_summary(analysis, log_filename)
        
        elif any(word in query_lower for word in ['suggest', 'recommend', 'advice']):
            analysis = self.analyze_log_patterns(log_content)
            return self.format_suggestions(analysis, log_filename)
        
        elif any(word in query_lower for word in ['count', 'how many', 'number']):
            return self.count_patterns(query, log_content)
        
        elif any(word in query_lower for word in ['find', 'search', 'locate']):
            return self.search_specific(query, log_content)
        
        else:
            return {
                'response': "I can help you analyze the log file. You can ask me about:\n- Errors and issues\n- Log summary\n- Suggestions and recommendations\n- Pattern counting\n- Specific searches\n\nTry asking: 'What errors are in this log?' or 'Give me a summary of issues'",
                'type': 'info'
            }
    
    def format_error_analysis(self, analysis, filename):
        response = f"## Error Analysis for {filename}\n\n"
        
        if analysis['errors']:
            response += f"**Found {len(analysis['errors'])} errors:**\n"
            for error in analysis['errors'][:5]:  # Show first 5 errors
                response += f"- {error}\n"
            if len(analysis['errors']) > 5:
                response += f"- ... and {len(analysis['errors']) - 5} more errors\n"
        else:
            response += "No errors detected in the analyzed portion.\n"
        
        return {'response': response, 'type': 'analysis'}
    
    def format_summary(self, analysis, filename):
        response = f"## Log Summary for {filename}\n\n"
        response += f"- **Errors found:** {len(analysis['errors'])}\n"
        response += f"- **Warnings found:** {len(analysis['warnings'])}\n"
        response += f"- **HTTP Status Codes:** {json.dumps(analysis['http_codes'], indent=2)}\n"
        response += f"- **Unique IPs:** {len(set(analysis['ips']))}\n"
        response += f"- **URLs accessed:** {len(analysis['urls'])}\n"
        
        return {'response': response, 'type': 'summary'}
    
    def format_suggestions(self, analysis, filename):
        response = f"## Recommendations for {filename}\n\n"
        
        for i, suggestion in enumerate(analysis['suggestions'], 1):
            response += f"{i}. {suggestion}\n"
        
        return {'response': response, 'type': 'suggestions'}
    
    def count_patterns(self, query, log_content):
        lines = log_content.split('\n')
        count = 0
        pattern = None
        
        # Extract search term from query
        words = query.lower().split()
        for word in words:
            if word not in ['count', 'how', 'many', 'number', 'of', 'the', 'in']:
                pattern = word
                break
        
        if pattern:
            for line in lines:
                if pattern in line.lower():
                    count += 1
            return {
                'response': f"Found {count} lines containing '{pattern}' in the log file.",
                'type': 'count'
            }
        else:
            return {
                'response': "Please specify what you want to count. Example: 'count errors' or 'how many warnings'",
                'type': 'info'
            }
    
    def search_specific(self, query, log_content):
        lines = log_content.split('\n')
        results = []
        search_term = None
        
        # Extract search term from query
        words = query.lower().split()
        for i, word in enumerate(words):
            if word in ['find', 'search', 'locate'] and i + 1 < len(words):
                search_term = words[i + 1]
                break
        
        if search_term:
            for i, line in enumerate(lines):
                if search_term in line.lower():
                    results.append(f"Line {i+1}: {line[:200]}...")
                    if len(results) >= 10:  # Limit results
                        break
            
            if results:
                response = f"**Found {len(results)} lines containing '{search_term}':**\n\n"
                for result in results:
                    response += f"- {result}\n"
                if len(results) == 10:
                    response += "\n*Showing first 10 results*"
            else:
                response = f"No lines found containing '{search_term}'"
            
            return {'response': response, 'type': 'search_results'}
        else:
            return {
                'response': "Please specify what you want to search for. Example: 'find error' or 'search timeout'",
                'type': 'info'
            }

# Initialize the log analyzer
log_analyzer = LogAnalyzer()



# --- AI Chat Routes ---
@app.route('/chat/<hostname_key>', methods=['GET', 'POST'])
def chat_interface(hostname_key):
    """Chat interface for log analysis"""
    if 'credentials' not in session or not session['credentials']:
        return redirect(url_for('authenticate'))
    
    HOST_CONFIG = get_host_config()
    credentials = get_host_credentials(hostname_key)
    if not credentials:
        return redirect(url_for('authenticate'))
    
    chat_history = session.get('chat_history', [])
    
    if request.method == 'POST':
        user_message = request.form.get('message', '')
        selected_log = request.form.get('selected_log', '')
        
        if user_message and selected_log:
            # Read the log file
            log_path = os.path.join(LOGS_DIR, selected_log)
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
                
                # Get AI response
                ai_response = log_analyzer.process_query(user_message, log_content, selected_log)
                
                # Update chat history
                chat_history.append({
                    'user': user_message,
                    'ai': ai_response['response'],
                    'type': ai_response['type'],
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'log_file': selected_log
                })
                
                # Keep only last 20 messages
                if len(chat_history) > 20:
                    chat_history = chat_history[-20:]
                
                session['chat_history'] = chat_history
                
            except Exception as e:
                error_msg = f"Error reading log file: {str(e)}"
                chat_history.append({
                    'user': user_message,
                    'ai': error_msg,
                    'type': 'error',
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'log_file': selected_log
                })
    
    # Get available log files
    hostname_config = HOST_CONFIG.get(hostname_key)
    client = _get_ssh_client(hostname_config, credentials['username'], credentials['password'])
    log_files = []
    if client:
        try:
            stdin, stdout, stderr = client.exec_command(f"ls {hostname_config['log_dir']}")
            log_files = stdout.read().decode().strip().split('\n')
            log_files = [f for f in log_files if f]  # Remove empty strings
            log_files.sort()
            client.close()
        except Exception as e:
            app_logger.error(f"Error fetching log files: {e}")
    
    return render_template('chat.html',
        hostname_key=hostname_key,
        hosts=HOST_CONFIG.keys(),
        log_files=log_files,
        chat_history=chat_history,
        username=session.get('current_user', 'Unknown')
    )

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    """Clear chat history"""
    session.pop('chat_history', None)
    return jsonify({'status': 'success'})

@app.route('/analyze_log/<hostname_key>/<path:filename>')
def analyze_log(hostname_key, filename):
    """Quick analysis of a log file"""
    if 'credentials' not in session or not session['credentials']:
        return jsonify({'error': 'Authentication required'}), 401
    
    log_path = os.path.join(LOGS_DIR, filename)
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
        
        analysis = log_analyzer.analyze_log_patterns(log_content)
        return jsonify(analysis)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
