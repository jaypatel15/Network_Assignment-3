import socketserver
import time

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

if __name__ == "__main__":
print(f" service is running.....")
