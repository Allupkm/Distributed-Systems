import socket
import threading
import time
import socketserver
import json
from contextlib import contextmanager
import os

# Change default HOST to listen on all interfaces instead of just localhost
HOST = '0.0.0.0'  # Listen on all network interfaces
PORT = 3000
# Get server name from environment variable or use default
SERVER_NAME = os.environ.get("SERVER_NAME", "Chat Server")
SERVERADDRESS = (HOST, PORT)
DISCOVERY_PORT = 3001  # Port for discovery service
BROADCAST_INTERVAL = 60  # Broadcast server presence every 60 seconds
HEARTBEAT_INTERVAL = 60
HEARTBEAT_TIMEOUT = 300

# Store clients using their nicknames - modified to store socket and last_active timestamp
clients = {}  # {nickname: {'socket': socket_obj, 'last_active': timestamp}}
clientsLock = threading.Lock()

# Store channels and their clients
channels = {"general": set()}
channelsLock = threading.Lock()

# Store recently disconnected users for reconnection (Improvement 7)
disconnected_users = {}  # {nickname: {'last_seen': timestamp, 'channel': channel_name}}
disconnected_timeout = 300  # 5 minutes to reconnect

# Context manager for acquiring locks in consistent order (prevents deadlocks)
@contextmanager
def acquire_locks():
    with clientsLock:
        with channelsLock:
            yield

# Helper functions for getting clients channel
def getUsersChannel(nickname, lockalreadyused=False):
    if not lockalreadyused:
        with channelsLock:
            for channel, users in channels.items():
                if nickname in users:
                    return channel
    else:
        # If lock is already held, don't try to acquire it again
        for channel, users in channels.items():
            if nickname in users:
                return channel
    return None

# Helper functions for deleting userdata
def deleteUserdata(nickname, locks_held=False):
    if not locks_held:
        with acquire_locks():  # Use context manager
            _delete_user_internal(nickname)
    else:
        _delete_user_internal(nickname)

def _delete_user_internal(nickname):
    for channel in channels.values():
        if nickname in channel:
            channel.discard(nickname)
    if nickname in clients:
        clients.pop(nickname, None)

# Helper function to handle client disconnect and other errors
def disconnectClient(nickname, locks_held=False, reason="unknown"):
    deleteUserdata(nickname, locks_held)
    print(f"{nickname} disconnected: {reason}")

# Function for broadcasting messages to all clients in a channel
def broadcast(message, channel, sender=None, clientSocket=None, locks_held=False):
    if not locks_held:
        with acquire_locks():  # Use context manager
            _broadcast_internal(message, channel, sender, clientSocket)
    else:
        _broadcast_internal(message, channel, sender, clientSocket)

def _broadcast_internal(message, channel, sender, clientSocket):
    if channel in channels:
        for nickname in channels[channel]:
            if nickname != sender and nickname in clients:
                try:
                    clients[nickname]['socket'].send(f"MSG:{message}".encode("utf-8"))
                    # Update last active time
                    clients[nickname]['last_active'] = time.time()
                except Exception as e:
                    print(f"Error sending to {nickname}: {e}")
                    # Direct modification since locks are held
                    for ch in channels.values():
                        if nickname in ch:
                            ch.discard(nickname)
                    clients.pop(nickname, None)
    
    # Confirm to sender their message was sent
    if sender and clientSocket:
        try:
            clientSocket.send(f"MSG_SENT:{message}".encode("utf-8"))
        except Exception as e:
            print(f"Error confirming to sender: {e}")

# Function for sending private messages
def privatemessage(message, sender, receiver, clientSocket):
    """Send private message from sender to receiver"""
    with clientsLock:
        if receiver in clients:
            try:
                clients[receiver]['socket'].send(f"PRIVATE:{sender}:{message}".encode("utf-8"))
                clientSocket.send(f"PRIVATE_SENT:{receiver}:{message}".encode("utf-8"))
                # Update last active time
                clients[receiver]['last_active'] = time.time()
                return True
            except Exception as e:
                print(f"Error sending DM: {e}")
                clientSocket.send(f"ERROR:Failed to send message to {receiver}".encode("utf-8"))
        else:
            clientSocket.send(f"ERROR:User {receiver} not found".encode("utf-8"))
    return False

# Command handler functions (Improvement 1)
def handle_join_command(msg, nickname, clientSocket):
    requestChannel = msg.split("JOIN:",1)[1].strip()
    
    # Use context manager
    with acquire_locks():
        currentChannel = getUsersChannel(nickname, True)
        if currentChannel and currentChannel != requestChannel:
            channels[currentChannel].discard(nickname)
            # Notify current channel members that user left
            broadcast(f"{nickname} has left the channel", currentChannel, None, None, True)
        if requestChannel not in channels:
            channels[requestChannel] = set()
        channels[requestChannel].add(nickname)
        clientSocket.send(f"INFO:Joined channel {requestChannel}".encode("utf-8"))
        broadcast(f"{nickname} has joined the channel", requestChannel, None, None, True)

def handle_msg_command(msg, nickname, clientSocket):
    message = msg.split("MSG:",1)[1].strip()
    
    # Use context manager
    with acquire_locks():
        currentChannel = getUsersChannel(nickname, True)
        if currentChannel:
            broadcast(message, currentChannel, nickname, clientSocket, True)
        else:
            clientSocket.send("ERROR:You are not in any channel".encode("utf-8"))

def handle_list_command(msg, nickname, clientSocket):
    listType = msg.split("LIST:",1)[1].strip().lower()
    if listType == "clients":
        with clientsLock:
            clientlist = ", ".join(clients.keys())
            clientSocket.send(f"CLIENTS:{clientlist}".encode("utf-8"))
    elif listType == "channels":
        with channelsLock:
            channellist = ", ".join(channels.keys())
            clientSocket.send(f"CHANNELS:{channellist}".encode("utf-8"))
    else:
        clientSocket.send("ERROR:Invalid list type. Use LIST:CLIENTS or LIST:CHANNELS".encode("utf-8"))

def handle_dm_command(msg, nickname, clientSocket):
    parts = msg.split("DM:",1)[1].split(":",1)
    if len(parts) == 2:
        receiver = parts[0].strip()
        content = parts[1].strip()
        privatemessage(content, nickname, receiver, clientSocket)
    else:
        clientSocket.send("ERROR:Invalid DM format".encode("utf-8"))

def handle_quit_command(msg, nickname, clientSocket):
    # Use context manager
    with acquire_locks():
        currentChannel = getUsersChannel(nickname, True)
        if currentChannel:
            broadcast(f"{nickname} has left the channel", currentChannel, nickname, clientSocket, True)
        disconnectClient(nickname, True, "quit")
    return True  # Signal to break the message loop

# Heartbeat check function
def heartbeat_check():
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        current_time = time.time()
        
        # Use context manager instead of nested with statements
        with acquire_locks():
            disconnected = []
            for nickname, client_info in clients.items():
                last_active = client_info.get('last_active', 0)
                if current_time - last_active > HEARTBEAT_TIMEOUT:
                    disconnected.append(nickname)
            
            for nickname in disconnected:
                client_socket = clients[nickname]['socket']
                try:
                    client_socket.close()
                except:
                    pass
                currentChannel = getUsersChannel(nickname, True)
                if currentChannel:
                    broadcast(f"{nickname} has been inactive for too long and was disconnected", currentChannel, None, None, True)
                    # For reconnection support - add to disconnected users
                    disconnected_users[nickname] = {
                        'last_seen': time.time(),
                        'channel': currentChannel
                    }
                disconnectClient(nickname, True)

# Periodically clean up old disconnected users
def clean_disconnected_users():
    while True:
        time.sleep(300)  # Check every 5 minutes
        current_time = time.time()
        to_remove = []
        for nickname, data in disconnected_users.items():
            if current_time - data['last_seen'] > disconnected_timeout:
                to_remove.append(nickname)
        
        for nickname in to_remove:
            disconnected_users.pop(nickname, None)
            print(f"Removed {nickname} from reconnection cache (timed out)")

# Request handler class for the server
class ChatRequestHandler(socketserver.BaseRequestHandler):
    def setup(self):
        # Initialize connection
        self.clientSocket = self.request
        self.clientAddress = self.client_address
        self.clientSocket.settimeout(300)  # Set socket timeout to 5 minutes
        print(f"Connection from {self.clientAddress}")
        self.nickname = None
    
    def handle(self):
        # Get nickname from client
        defaultChannel = "general"
        try:
            while not self.nickname: # Get nickname from client
                msg = self.clientSocket.recv(1024).decode("utf-8")
                if msg.startswith("NICKNAME:"):
                    requestNickname = msg.split("NICKNAME:",1)[1].strip()
                    with clientsLock: # Check if nickname is already taken
                        nicknameTaken = False
                        for existingNickname in clients.keys():
                            if existingNickname.lower() == requestNickname.lower():
                                nicknameTaken = True
                                break
                        
                        if nicknameTaken:
                            self.clientSocket.send("ERROR:Nickname already taken".encode("utf-8"))
                        else:
                            self.nickname = requestNickname
                            clients[self.nickname] = {
                                'socket': self.clientSocket,
                                'last_active': time.time()
                            }
                            self.clientSocket.send(f"INFO:Welcome {self.nickname}".encode("utf-8"))
                    
                    # IMPORTANT: Skip the rest of the loop if nickname wasn't accepted
                    if not self.nickname:
                        continue
                    
                    # Check if this is a reconnection (Improvement 7)
                    if self.nickname in disconnected_users:
                        reconnect_data = disconnected_users[self.nickname]
                        if time.time() - reconnect_data['last_seen'] < disconnected_timeout:
                            rejoin_channel = reconnect_data['channel']
                            
                            # Use context manager
                            with acquire_locks():
                                # Add to previous channel instead of default
                                if rejoin_channel in channels:
                                    channels[rejoin_channel].add(self.nickname)
                                    self.clientSocket.send(f"INFO:Reconnected to previous channel {rejoin_channel}".encode("utf-8"))
                                    broadcast(f"{self.nickname} has reconnected to the channel", rejoin_channel, None, None, True)
                                    # Remove from disconnected users
                                    disconnected_users.pop(self.nickname, None)
                                    continue  # Skip adding to default channel
                    
                    # If not reconnecting, add to default channel
                    # Use context manager
                    with acquire_locks():
                        channels[defaultChannel].add(self.nickname)
                        broadcast(f"{self.nickname} has joined the channel {defaultChannel}", defaultChannel, None, None, True)

            # Command handlers dictionary (Improvement 1)
            command_handlers = {
                "JOIN": handle_join_command,
                "MSG": handle_msg_command,
                "LIST": handle_list_command,
                "DM": handle_dm_command,
                "QUIT": handle_quit_command
            }

            while True:
                msg = self.clientSocket.recv(1024).decode("utf-8")
                if not msg:
                    break
                
                # Update last active time on each message
                with clientsLock:
                    if self.nickname in clients:
                        clients[self.nickname]['last_active'] = time.time()
                
                # Extract command and use command handlers (Improvement 1)
                command = msg.split(":", 1)[0] if ":" in msg else msg
                
                if command in command_handlers:
                    # Call the appropriate handler
                    result = command_handlers[command](msg, self.nickname, self.clientSocket)
                    if result:  # If handler returns True, break the loop (for QUIT)
                        self.clientSocket.close()
                        break
                else:
                    self.clientSocket.send("ERROR:Unknown command".encode("utf-8"))
                    
        except socket.timeout:
            print(f"Connection timeout: {self.clientAddress}")
            # Add to disconnected users for possible reconnection (Improvement 7)
            with acquire_locks():  # Use context manager
                currentChannel = getUsersChannel(self.nickname, True)
                if currentChannel and self.nickname:
                    disconnected_users[self.nickname] = {
                        'last_seen': time.time(),
                        'channel': currentChannel
                    }
        except Exception as e:
            print(f"Error handling client {self.clientAddress}: {e}")
            # Add to disconnected users for possible reconnection (Improvement 7)
            if self.nickname:
                with acquire_locks():  # Use context manager
                    currentChannel = getUsersChannel(self.nickname, True)
                    if currentChannel:
                        disconnected_users[self.nickname] = {
                            'last_seen': time.time(),
                            'channel': currentChannel
                        }

    def finish(self):
        # Clean up when connection is closed
        if self.nickname: 
            with acquire_locks():  # Use context manager
                currentChannel = getUsersChannel(self.nickname, True)
                if currentChannel:
                    broadcast(f"{self.nickname} has left the channel", currentChannel, self.nickname, None, True)
                # Only disconnect if it was an intentional QUIT (handled by command handler)
                # Otherwise, keep in disconnected_users for potential reconnection
                if self.nickname not in disconnected_users:
                    disconnectClient(self.nickname, True, "connection lost")
                else:
                    # Just remove from active clients but keep in disconnected_users
                    _delete_user_internal(self.nickname)
            try:
                self.clientSocket.close()
            except:
                pass
            print(f"Connection closed: {self.clientAddress}")

# Threading TCP Server with allow_reuse_address enabled
class ChatServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True  # Allows reuse of address/port

# Add this new function for the discovery service
def run_discovery_service():
    """Run a UDP service that responds to discovery broadcasts"""
    discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Allow receiving broadcasts
    discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    # Bind to discovery port
    discovery_socket.bind(('', DISCOVERY_PORT))
    
    print(f"Discovery service running on port {DISCOVERY_PORT}")
    
    while True:
        try:
            # Wait for discovery requests
            data, addr = discovery_socket.recvfrom(1024)
            message = data.decode('utf-8')
            
            # Respond to discovery requests
            if message == "CHAT_SERVER_DISCOVERY":
                # Get the local IP address
                local_ip = socket.gethostbyname(socket.gethostname())
                
                # Create server info packet
                server_info = {
                    "name": SERVER_NAME,
                    "ip": local_ip,
                    "port": PORT,
                    "clients": len(clients)
                }
                
                # Send response
                discovery_socket.sendto(json.dumps(server_info).encode('utf-8'), addr)
                print(f"Sent discovery response to {addr}")
        except Exception as e:
            print(f"Error in discovery service: {e}")
            time.sleep(1)  # Prevent tight loop on error

# Add this function to broadcast server presence
def broadcast_server_presence():
    """Periodically broadcast server presence to the local network"""
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    while True:
        try:
            # Get the local IP address
            local_ip = socket.gethostbyname(socket.gethostname())
            
            # Create server announcement packet
            server_info = {
                "name": SERVER_NAME,
                "ip": local_ip,
                "port": PORT,
                "clients": len(clients),
                "announcement": "SERVER_AVAILABLE"
            }
            
            # Broadcast to the local network
            broadcast_socket.sendto(
                json.dumps(server_info).encode('utf-8'), 
                ('<broadcast>', DISCOVERY_PORT)
            )
            print(f"Broadcast server presence: {SERVER_NAME} at {local_ip}:{PORT}")
            
            # Wait before next broadcast
            time.sleep(BROADCAST_INTERVAL)
        except Exception as e:
            print(f"Error broadcasting server presence: {e}")
            time.sleep(5)  # Shorter delay on error

# Add these imports and functions:
import json
import os

# Registry configuration
REGISTRY_HOST = "localhost"  # Change to IP if registry is on different machine
REGISTRY_PORT = 3999
SERVER_NAME = os.environ.get("SERVER_NAME", "Chat Server")

def register_with_registry():
    """Register this server with the registry service"""
    try:
        registry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Registration message
        registration = {
            "action": "REGISTER",
            "name": SERVER_NAME,
            "port": PORT
        }
        
        # Send registration
        registry_socket.sendto(json.dumps(registration).encode("utf-8"), 
                              (REGISTRY_HOST, REGISTRY_PORT))
        
        # Wait for confirmation
        registry_socket.settimeout(5.0)
        try:
            data, _ = registry_socket.recvfrom(1024)
            response = json.loads(data.decode("utf-8"))
            
            if response.get("status") == "success":
                print(f"Successfully registered with registry as '{SERVER_NAME}'")
            else:
                print(f"Failed to register with registry: {response.get('message')}")
        except socket.timeout:
            print("No response from registry server")
            
    except Exception as e:
        print(f"Error registering with registry: {e}")

def send_heartbeats():
    """Periodically send heartbeats to the registry"""
    heartbeat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    while True:
        try:
            # Create heartbeat message
            heartbeat = {
                "action": "HEARTBEAT",
                "name": SERVER_NAME
            }
            
            # Send heartbeat
            heartbeat_socket.sendto(json.dumps(heartbeat).encode("utf-8"),
                                   (REGISTRY_HOST, REGISTRY_PORT))
                                   
        except Exception as e:
            print(f"Error sending heartbeat: {e}")
            
        time.sleep(60)  # Send heartbeat every minute

# Modify the startServer function to include registry
def startServer():
    # Create server instance
    server = ChatServer(SERVERADDRESS, ChatRequestHandler)
    print(f"Server started on {HOST}:{PORT}")
    
    # Register with the registry
    register_with_registry()
    
    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=send_heartbeats)
    heartbeat_thread.daemon = True
    heartbeat_thread.start()
    
    # Start heartbeat checking thread
    heartbeatThread = threading.Thread(target=heartbeat_check)
    heartbeatThread.daemon = True
    heartbeatThread.start()
    
    # Start cleanup thread for disconnected users
    cleanup_thread = threading.Thread(target=clean_disconnected_users)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    # Start discovery service thread
    discovery_thread = threading.Thread(target=run_discovery_service)
    discovery_thread.daemon = True
    discovery_thread.start()
    
    # Start server announcement thread
    announcement_thread = threading.Thread(target=broadcast_server_presence)
    announcement_thread.daemon = True
    announcement_thread.start()
    
    try:
        # Run the server until interrupted
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server shutting down...")
        with clientsLock:
            for client_info in clients.values():
                try:
                    client_info['socket'].send("INFO:Server is shutting down".encode("utf-8"))
                    client_info['socket'].close()
                except:
                    pass
        server.server_close()
        print("Server stopped")

# Start server
if __name__ == "__main__":
    startServer()