from flask import Flask, send_from_directory
import os
import platform
import subprocess
from datetime import datetime
from openai import OpenAI
import re

# Initialize the OpenAI client with your API key
client = OpenAI(api_key="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")

# Initialize the Flask app
app = Flask(__name__)

# Log file setup
LOG_FILE = "flask_openai_app.log"

def log_event(event_type, message):
    """
    Logs events to a log file with timestamps.
    :param event_type: Type of event (e.g., INFO, ERROR, COMMAND).
    :param message: The message to log.
    """
    with open(LOG_FILE, "a") as log_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"[{timestamp}] {event_type}: {message}\n")

def ai_request(prompt):
    """
    Sends a prompt to OpenAI's API and returns the response.
    :param prompt: The user's query or command to process.
    :return: The AI-generated response.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Replace with your preferred OpenAI model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates terminal commands, corrects errors, and creates/manage files dynamically."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "text"},
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        result = response.choices[0].message.content.strip()
        log_event("INFO", f"AI Response: {result}")
        return result
    except Exception as e:
        log_event("ERROR", f"AI Request Error: {e}")
        return f"Error: {e}"

def execute_terminal_command(command):
    """
    Executes a terminal command and captures the output or error.
    :param command: The command to execute.
    :return: A tuple (success, output/error).
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        log_event("COMMAND", f"Executed Command: {command}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip()
        log_event("ERROR", f"Command Error: {error_message}")
        return False, error_message

def setup_html_file(folder_name, file_name):
    """
    Ensures the specified folder and file exist. Creates them if necessary.
    :param folder_name: Name of the folder to create or check.
    :param file_name: Name of the file to create or check.
    :return: Full path to the file.
    """
    # Ensure the folder exists
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        log_event("INFO", f"Created folder: {folder_name}")

    # Create the HTML file if it doesn't exist
    file_path = os.path.join(folder_name, file_name)
    if not os.path.exists(file_path):
        with open(file_path, "w") as file:
            file.write("""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Local Flask App</title>
            </head>
            <body>
                <h1>Hello, World!</h1>
                <p>This is a simple HTML file served via Flask.</p>
            </body>
            </html>
            """)
        log_event("INFO", f"Created HTML file: {file_path}")
    return file_path

def handle_placeholders(command):
    """
    Detects placeholders (e.g., <directory_name>) and prompts the user for replacement values.
    :param command: The command with potential placeholders.
    :return: The command with placeholders replaced by user input.
    """
    placeholders = re.findall(r"<(.*?)>", command)
    for placeholder in placeholders:
        user_input = input(f"Replace <{placeholder}>: ").strip()
        if not user_input:
            print(f"Invalid input for {placeholder}. Please try again.")
            user_input = input(f"Replace <{placeholder}>: ").strip()
        command = command.replace(f"<{placeholder}>", user_input, 1)
    return command

@app.route("/")
def serve_file():
    """
    Serves the HTML file from the specified folder.
    """
    return send_from_directory(folder_name, file_name)

def start_server():
    """
    Starts the Flask server and serves the HTML file.
    """
    try:
        # Determine the local IP address
        local_ip = os.popen('hostname -I').read().strip().split()[0]  # For Linux/Unix
        if not local_ip:
            log_event("ERROR", "Could not determine local IP address.")
            print("Error: Could not determine your local IP address. Ensure your network is active.")
            exit(1)

        log_event("INFO", f"Starting Flask server at http://{local_ip}:5000")
        print(f"Serving the application at http://{local_ip}:5000")
        print("Connect devices on the same network or hotspot to access the app.")
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        log_event("ERROR", f"Error starting server: {e}")
        print(f"Error: Could not start the Flask server. Check logs for details.")
        exit(1)

def process_query(user_query):
    """
    Processes user queries to generate and execute terminal commands.
    Includes error correction and re-execution.
    :param user_query: The user's input or query.
    """
    try:
        log_event("INFO", f"User Query: {user_query}")
        
        # Send the query to OpenAI for analysis and command generation
        analysis_prompt = (
            f"Analyze this query: '{user_query}'. "
            "If it's a terminal command, provide it as 'Command: <command>'. Otherwise, respond conversationally."
        )
        ai_response = ai_request(analysis_prompt)
        
        if "Command:" in ai_response:
            terminal_command = ai_response.split("Command:")[1].strip()
            terminal_command = handle_placeholders(terminal_command)
            
            print(f"Generated Command: {terminal_command}")
            log_event("INFO", f"Generated Command: {terminal_command}")
            
            success, output = execute_terminal_command(terminal_command)
            if success:
                print(f"Command Output:\n{output}")
            else:
                print(f"Command failed with error:\n{output}")
        else:
            print(ai_response)
    except Exception as e:
        error_message = f"Error processing query: {e}"
        print(error_message)
        log_event("ERROR", error_message)

if __name__ == "__main__":
    # Prompt user for folder and file names
    folder_name = input("Enter the folder name to serve files from (default: 'shared_folder'): ").strip() or "shared_folder"
    file_name = input("Enter the HTML file name (default: 'index.html'): ").strip() or "index.html"

    # Set up the folder and file
    setup_html_file(folder_name, file_name)

    # Start the Flask server
    start_server()
