import socketserver
import time
import json
import datetime
import uuid
import threading

client_timestamps = {}
rate_lock = threading.Lock()

def is_rate_allowed(client_ip, max_msgs):
    now = time.time()
    with rate_lock:
        timestamps = client_timestamps.get(client_ip, [])
        timestamps = [t for t in timestamps if now - t < 1]  
        if len(timestamps) >= max_msgs:
            client_timestamps[client_ip] = timestamps
            return False
        timestamps.append(now)
        client_timestamps[client_ip] = timestamps
    return True

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class LoggingHandler(socketserver.BaseRequestHandler):
    connection_tracker = set()  

    def handle(self):
        client_ip = self.client_address[0]
        if client_ip not in LoggingHandler.connection_tracker:
            print(f" Connection established with {client_ip}")
            LoggingHandler.connection_tracker.add(client_ip)

        self.request.settimeout(self.server.timeout)
        data = b''
        start_time = time.time()
        delimiter = b'\n' 
        
        while time.time() - start_time < self.server.timeout:
            try:
                chunk = self.request.recv(4096)
                if chunk:
                    data += chunk
                    if delimiter in data:
                        break 
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
            payload = json.loads(data.decode('utf-8'))
            log_level = payload.get("logLevel", "INFO")
            log_message = payload.get("logMessage", "No message provided")

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

            
        try:
            with self.server.file_lock:
                with open(self.server.log_file, "a") as f:
                    f.write(custom_format + "\n")
            print(f" Logged message from {client_ip}: {custom_format}")
        except Exception as e:
            print(f" Failed to write log entry: {e}")
        
        self.request.sendall(f"Logged: {custom_format}".encode('utf-8'))


if __name__ == "__main__":
print(f" service is running.....")
