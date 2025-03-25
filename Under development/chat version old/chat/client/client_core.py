import socket
import threading
import time
import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("chat_app.log"),
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger(__name__)

def generate_key(password: str, salt: bytes) -> bytes:
    """Generate encryption key from password"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_message(message: str, key: bytes) -> str:
    """Encrypt a message"""
    f = Fernet(key)
    return f.encrypt(message.encode()).decode()

def decrypt_message(encrypted_message: str, key: bytes) -> str:
    """Decrypt a message"""
    f = Fernet(key)
    return f.decrypt(encrypted_message.encode()).decode()

class ChatClient:
    def __init__(self, message_callback, status_callback):
        self.clientSocket = None
        self.running_event = threading.Event()
        self.message_callback = message_callback
        self.status_callback = status_callback
        self.nickname = None
        self.current_channel = "general"
        self.quitting = False
        
    def connect(self, host, port, nickname):
        """Connect to the chat server"""
        self.host = host
        self.port = port
        self.nickname = nickname
        self.quitting = False
        
        try:
            self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.clientSocket.connect((host, port))
            
            # Send nickname
            self.clientSocket.send(f"NICKNAME:{nickname}".encode("utf-8"))
            
            # Start threads
            self.running_event.set()
            
            # Start message receiving thread
            receive_thread = threading.Thread(target=self._receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Start keep-alive thread
            keepalive_thread = threading.Thread(target=self._keep_alive)
            keepalive_thread.daemon = True
            keepalive_thread.start()
            
            self.status_callback("connected", f"Connected to {host}:{port}")
            logger.info("Connected to server")
            
            # Request initial lists after connecting (add this)
            threading.Timer(1.0, self.list_clients).start()
            threading.Timer(1.5, self.list_channels).start()
            
            return True
            
        except Exception as e:
            self.status_callback("error", f"Error connecting to server: {e}")
            logger.error(f"Error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        if not self.running_event.is_set():
            return
            
        try:
            self.quitting = True
            self.clientSocket.send("QUIT".encode("utf-8"))
            self.running_event.clear()
            time.sleep(0.5)  # Give server time to process
            self.clientSocket.close()
            self.status_callback("disconnected", "Disconnected from server")
        except Exception as e:
            self.status_callback("error", f"Error disconnecting: {e}")
            logger.error(f"Error: {e}")
    
    def send_message(self, message):
        """Send a message to the current channel"""
        try:
            self.clientSocket.send(f"MSG:{message}".encode("utf-8"))
            return True
        except Exception as e:
            self.status_callback("error", f"Error sending message: {e}")
            logger.error(f"Error: {e}")
            return False
    
    def join_channel(self, channel):
        """Join a channel"""
        try:
            self.clientSocket.send(f"JOIN:{channel}".encode("utf-8"))
            return True
        except Exception as e:
            self.status_callback("error", f"Error joining channel: {e}")
            logger.error(f"Error: {e}")
            return False
    
    def send_dm(self, recipient, message):
        """Send a direct message"""
        try:
            self.clientSocket.send(f"DM:{recipient}:{message}".encode("utf-8"))
            return True
        except Exception as e:
            self.status_callback("error", f"Error sending DM: {e}")
            logger.error(f"Error: {e}")
            return False
    
    def list_channels(self):
        """Request list of channels"""
        try:
            self.clientSocket.send("LIST:CHANNELS".encode("utf-8"))
            return True
        except Exception as e:
            self.status_callback("error", f"Error listing channels: {e}")
            logger.error(f"Error: {e}")
            return False
    
    def list_clients(self):
        """Request list of clients"""
        try:
            self.clientSocket.send("LIST:CLIENTS".encode("utf-8"))
            return True
        except Exception as e:
            self.status_callback("error", f"Error listing clients: {e}")
            logger.error(f"Error: {e}")
            return False
    
    def save_chat_history(self, channel):
        """Save current channel's messages to file"""
        if not os.path.exists("chat_history"):
            os.makedirs("chat_history")
        with open(f"chat_history/{self.nickname}_{channel}.txt", "w") as f:
            # Save history from message display
            pass
        
    def load_chat_history(self, channel):
        """Load chat history for channel"""
        try:
            with open(f"chat_history/{self.nickname}_{channel}.txt", "r") as f:
                # Load and display history
                pass
        except FileNotFoundError:
            pass
    
    def send_file(self, filepath):
        """Send a file to the current channel"""
        if os.path.exists(filepath) and os.path.getsize(filepath) < 10485760:  # 10MB limit
            filename = os.path.basename(filepath)
            with open(filepath, 'rb') as file:
                file_data = file.read()
                encoded_data = base64.b64encode(file_data).decode('utf-8')
                
                # Send in chunks if large
                chunk_size = 4096
                chunks = [encoded_data[i:i+chunk_size] for i in range(0, len(encoded_data), chunk_size)]
                
                # Start file transfer
                self.clientSocket.send(f"FILE_START:{filename}:{len(chunks)}".encode("utf-8"))
                
                for i, chunk in enumerate(chunks):
                    self.clientSocket.send(f"FILE_CHUNK:{i}:{chunk}".encode("utf-8"))
                    time.sleep(0.01)  # Prevent overwhelming the server
                    
                self.clientSocket.send(f"FILE_END:{filename}".encode("utf-8"))
                return True
        else:
            self.status_callback("error", "File not found or exceeds size limit (10MB)")
            logger.error("File not found or exceeds size limit (10MB)")
            return False
    
    def create_channel(self, channel_name):
        """Create a new channel"""
        try:
            self.clientSocket.send(f"CREATE_CHANNEL:{channel_name}".encode("utf-8"))
            return True
        except Exception as e:
            self.status_callback("error", f"Error creating channel: {e}")
            logger.error(f"Error: {e}")
            return False

    def delete_channel(self, channel_name):
        """Delete a channel (admin only)"""
        try:
            self.clientSocket.send(f"DELETE_CHANNEL:{channel_name}".encode("utf-8"))
            return True
        except Exception as e:
            self.status_callback("error", f"Error deleting channel: {e}")
            logger.error(f"Error: {e}")
            return False
    
    def _receive_messages(self):
        """Thread function to receive messages"""
        try:
            while self.running_event.is_set():
                try:
                    message = self.clientSocket.recv(1024).decode("utf-8")
                    if not message:
                        if not self.quitting:
                            self.status_callback("error", "Connection to server lost")
                            logger.error("Connection to server lost")
                        self.running_event.clear()
                        self.status_callback("disconnected", "")
                        return
                    
                    # Process message based on prefix
                    self._process_message(message)
                    
                except socket.timeout:
                    continue
                except ConnectionError as e:
                    if not self.quitting:
                        self.status_callback("error", f"Connection error: {e}")
                        logger.error(f"Connection error: {e}")
                    self.running_event.clear()
                    self.status_callback("disconnected", "")
                    return
        except Exception as e:
            if not self.quitting:
                self.status_callback("error", f"Error receiving messages: {e}")
                logger.error(f"Error receiving messages: {e}")
            self.running_event.clear()
            self.status_callback("disconnected", "")
    
    def _process_message(self, message):
        """Process received messages"""
        if message.startswith("MSG:"):
            self.message_callback("message", message[4:])
        elif message.startswith("MSG_SENT:"):
            self.message_callback("message_sent", message[9:])
        elif message.startswith("PRIVATE:"):
            parts = message.split(":", 2)
            if len(parts) >= 3:
                sender = parts[1]
                content = parts[2]
                self.message_callback("dm_received", (sender, content))
        elif message.startswith("PRIVATE_SENT:"):
            parts = message.split(":", 2)
            if len(parts) >= 3:
                receiver = parts[1]
                content = parts[2]
                self.message_callback("dm_sent", (receiver, content))
        elif message.startswith("CLIENTS:"):
            self.message_callback("clients", message[8:])
        elif message.startswith("CHANNELS:"):
            self.message_callback("channels", message[9:])
        elif message.startswith("INFO:"):
            if "Server is shutting down" in message:
                self.message_callback("system", "Server is shutting down gracefully")
                self.running_event.clear()
                self.status_callback("disconnected", "")
                return
            elif "Joined channel" in message:
                # Extract channel name
                channel = message[message.rfind(" ")+1:]
                self.current_channel = channel
                self.message_callback("system", message[5:])
            elif "Reconnected to previous channel" in message:
                # Extract channel name
                channel = message[message.rfind(" ")+1:]
                self.current_channel = channel
                self.message_callback("system", message[5:])
            else:
                self.message_callback("system", message[5:])
        elif message.startswith("ERROR:"):
            self.message_callback("error", message[6:])
        elif message.startswith("QUIT"):
            self.message_callback("system", "Server disconnected")
            self.running_event.clear()
            self.status_callback("disconnected", "")
            return
        elif message.startswith("HEARTBEAT"):
            # Silent handling of server heartbeat messages
            pass
        else:
            self.message_callback("other", message)
    
    def _keep_alive(self):
        """Thread function to keep connection alive and refresh lists"""
        refresh_counter = 0
        while self.running_event.is_set():
            time.sleep(60)  # Check every minute
            try:
                if self.running_event.is_set():
                    refresh_counter += 1
                    
                    # Every 4th time (4 minutes) do the full LIST:CLIENTS for heartbeat
                    if refresh_counter >= 4:
                        self.clientSocket.send("LIST:CLIENTS".encode("utf-8"))
                        refresh_counter = 0
                    
                    # On other minutes, alternate between refreshing clients and channels
                    elif refresh_counter % 2 == 1:
                        self.list_clients()
                    else:
                        self.list_channels()
            except:
                pass  # Let the receive thread handle any errors