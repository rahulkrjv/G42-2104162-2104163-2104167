import json
import os
import subprocess
import sys
from flask import Flask, render_template, send_from_directory, Response
from flask_socketio import SocketIO, emit
import requests
import openai

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

def generate_response(cmd: str, code: str) -> str:
    model_engine = "local-model"  # Set the desired LLM model engine
    base_url = "http://localhost:1234/v1"

    # Create the request payload with user input and relevant passage
    payload = {
    "messages": [
        {"role": "system", "content": "This is the python code, do as commanded and output should only be a python code.:\n\n" + code},
        {"role": "user", "content": cmd}
    ],
    "temperature": 0.7,
    "max_tokens": -1,
    "stream": False
}

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        response.raise_for_status()

        # Extract the generated response from the API response
        generated_response = response.json()["choices"][0]["message"]["content"].strip()
        return generated_response

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while generating the response: {str(e)}")
        return "None"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/language-server', methods=['POST'])
def language_server():
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), 'pylance')
    process = subprocess.Popen(['python', '-m', 'pylance', '--stdio'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    while True:
        request = request.get_json()
        request['initialize']['params']['initializationOptions'] = {'analysis': {'diagnosticSeverityOverrides': {'error': 'error', 'warning': 'warning', 'information': 'information', 'hint': 'hint'}}}
        request_str = json.dumps(request)
        process.stdin.write(request_str.encode())
        process.stdin.flush()
        response_str = process.stdout.readline().decode()
        response = json.loads(response_str)
        print("Response: ", response)

        if 'errors' in response:
            emit('code editor errors', response['errors'])
        if 'diagnostics' in response:
            emit('code editor diagnostics', response['diagnostics'])
        yield response_str

@app.route('/flake8', methods=['POST'])
def flake8():
    code = requests.request.get_json()['code']
    
    # Write the code to a temporary Python file
    with open('temp.py', 'w') as f:
        f.write(code)

    # Run Flake8 on the temporary Python file
    process = subprocess.Popen(['flake8', 'temp.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()

    # Remove the temporary Python file
    os.remove('temp.py')

    # If Flake8 finds any issues, they will be in the stderr
    # Convert the stderr to a list of strings, each representing an issue
    issues = error.decode().split('\n') if error else []

    # Remove any empty strings from the list of issues
    issues = [issue for issue in issues if issue]

    # Return the list of issues as a JSON response
    return Response(json.dumps(issues), mimetype='application/json')

@socketio.on('terminal command')
def handle_terminal_command(code):
    with open('temp.py', 'w') as f:
        f.write(code)

    process = subprocess.Popen(['powershell.exe', '-Command', "python temp.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize=1)
    for line in process.stdout:
        emit('terminal output', line)
    for line in process.stderr:
        emit('terminal output', line)

@socketio.on('run code')
def run_code(data):
    print("running")
    code = data['code']
    command = data['command']

    # Save the code in a .py file
    with open('temp.py', 'w') as f:
        f.write(code)

    # Run the .py file using the subprocess module
    if command == 'complete':
        response = generate_response(cmd=command, code=code)
        with open('temp.md', 'w') as f:
            f.write(response)
        emit('code response', {'response': response})

    elif command == 'optimize':
        response = generate_response(cmd=command, code=code)
        with open('temp.md', 'w') as f:
            f.write(response)
        emit('code response', {'response': response})

    elif command == 'custom':
        response = generate_response(cmd=command, code=code)
        with open('temp.md', 'w') as f:
            f.write(response)
        emit('code response', {'response': response})

    else:
        process = subprocess.Popen(['python', 'temp.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        emit('code response', {'response': output.decode() if output else error.decode()})


if __name__ == '__main__':
    socketio.run(app)
