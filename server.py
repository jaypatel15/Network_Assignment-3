"""
    Name        : Jay Patel  (8888384)
                  Helly Shah (8958841)
    Project Name: Server.py
    Date        : 25th February, 2025
    Description : A TCP logging server with rate limiting and file logging.
"""
# https://docs.python.org/3/library/socketserver.html
# https://www.geeksforgeeks.org/python-programming-language-tutorial/

import socketserver
import time
import json
import datetime
import uuid
import threading
import argparse

client_timestamps = {}   # Track request timestamps per client
rate_lock = threading.Lock()  # Ensure thread-safe access

def is_rate_allowed(client_ip, max_msgs):
    now = time.time()
    with rate_lock:
        timestamps = client_timestamps.get(client_ip, [])
        timestamps = [t for t in timestamps if now - t < 1]  # Keep only recent timestamps
        if len(timestamps) >= max_msgs:
            client_timestamps[client_ip] = timestamps
            return False    # Exceeded rate limit
        timestamps.append(now)
        client_timestamps[client_ip] = timestamps
    return True

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass  # Enables multithreading support

class LoggingHandler(socketserver.BaseRequestHandler):
    connection_tracker = set()  # Track active connections

    def handle(self):
        client_ip = self.client_address[0]
        if client_ip not in LoggingHandler.connection_tracker:
            print(f" Connection established with {client_ip}")
            LoggingHandler.connection_tracker.add(client_ip)

        self.request.settimeout(self.server.timeout)
        data = b''
        start_time = time.time()
        delimiter = b'\n'  # Define message delimiter
        
        while time.time() - start_time < self.server.timeout:
            try:
                chunk = self.request.recv(4096) # Receive data
                if chunk:
                    data += chunk
                    if delimiter in data:
                        break # Stop when a complete message is received
                else:
                    break  
            except socket.timeout:
                continue 
        
        if not data:
            time.sleep(self.server.timeout)  # Wait for the configured timeout duration
            print(f" No data received from {client_ip}, closing connection.")
            return

        try:

            data = data.rstrip(delimiter)
            payload = json.loads(data.decode('utf-8'))  # Parse JSON
            log_level = payload.get("logLevel", "INFO")
            log_message = payload.get("logMessage", "No message provided")
            # Format log entry with timestamp, client IP, log level, and message
            custom_format = self.server.log_format.format(
                timestamp=datetime.datetime.now(
                    datetime.timezone(datetime.timedelta(hours=self.server.tz_offset))
                ).isoformat() + "Z",
                client=client_ip,
                level=log_level,
                message=log_message,
                correlationId=str(uuid.uuid4())
            )

        except Exception:
            print(f" Malformed log data from {client_ip}")
            return

        if not is_rate_allowed(client_ip, self.server.max_msgs):
            response = "Rate limit exceeded. Please slow down."
            self.request.sendall(response.encode('utf-8'))
            print(f"Rate limit exceeded for {client_ip}") 
            return
            
        try:
            with self.server.file_lock:
                with open(self.server.log_file, "a") as f:
                    f.write(custom_format + "\n") # Append log entry
            print(f" Logged message from {client_ip}: {custom_format}")
        except Exception as e:
            print(f" Failed to write log entry: {e}")
        
        self.request.sendall(f"Logged: {custom_format}".encode('utf-8'))  # Send response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="", help="Host/IP to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port number to bind")
    parser.add_argument("--logfile", default="logs.txt", help="Path to log file")
    parser.add_argument("--max", type=int, default=100, help="Max messages per client per second")
    parser.add_argument("--format", default="[{timestamp}] {client} {level}: {message} (ID: {correlationId})", help="Log message format")
    parser.add_argument("--timeout", type=int, default=600, help="Client socket timeout in seconds") 
    parser.add_argument("--tz_offset", type=int, default=-5, help="Timezone offset in hours from UTC")   
    args = parser.parse_args()

    # Initialize server with user-defined parameters
    server = ThreadedTCPServer((args.host, args.port), LoggingHandler)
    server.log_file = args.logfile
    server.max_msgs = args.max
    server.log_format = args.format
    server.file_lock = threading.Lock()
    server.timeout = args.timeout
    server.tz_offset = args.tz_offset

    print(f" service is running.....")
     try:
        server.serve_forever() # Start server
    except KeyboardInterrupt:
        print(" Server shutting down gracefully.")
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()