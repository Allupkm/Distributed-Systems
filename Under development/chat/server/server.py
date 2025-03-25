import socket
import threading
import time
from contextlib import contextmanager
from datetime import datetime

# Defaults for creation process so localhost
HOST = '0.0.0.0'
PORT = 3000
SERVERADDRESS = (HOST, PORT)

def get_local_ip():
    try:
        # Create a socket connection to an external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't actually connect but helps determine the interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Could not determine local IP. Try 'ipconfig' on Windows or 'ifconfig' on Linux/Mac"


# Values for checking client connection
clientTimeout = 60
clientsCheckInterval = 30

# message history
messageHistory = {}
MAX_HISTORY = 20

# Context manager for acquiring locks
@contextmanager
def acquirelocks():
    with clientsLock:
        with channelsLock:
            yield

# Store clients using their nicknames
clients = {}
clientsLock = threading.Lock()

# Store channels and their clients
channels = {"general": set()}
channelsLock = threading.Lock()

# Function for starting server
def startServer():
    # Create a socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSocket.bind(SERVERADDRESS)
    serverSocket.listen()
    local_ip = get_local_ip()
    print(f"Server started and listening on all interfaces (0.0.0.0:{PORT})")
    print(f"For clients to connect on your network, use this address: {local_ip}:{PORT}")
    print(f"For local connections, use: 127.0.0.1:{PORT}")
    
    # Start the client connection checker thread
    connectionCheckerThread = threading.Thread(target=checkClientConnection)
    connectionCheckerThread.daemon = True
    connectionCheckerThread.start()
    
    try:
        while True:
            # Wait for a connection
            clientSocket, clientAddress = serverSocket.accept()
            print(f"Connection from {clientAddress}")
            clientThread = threading.Thread(target=handleClient, args=(clientSocket, clientAddress))
            clientThread.daemon = True
            clientThread.start()
    except KeyboardInterrupt:
        for client in clients.values():
            try:
                timestamp = datetime.now().strftime("%H.%M")
                client['socket'].send(f"ERROR:{timestamp}:Server is shutting down".encode("utf-8"))
                client['socket'].close()
            except:
                pass
        serverSocket.close()
        print("Server stopped")

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
    """Remove user data from all collections"""
    # Use acquirelocks for consistency instead of separate locks
    if not locks_held:
        with acquirelocks():
            # Remove from all channels
            for channel in channels.values():
                if nickname in channel:
                    channel.discard(nickname)
            
            # Remove from clients dictionary
            if nickname in clients:
                clients.pop(nickname, None)
    else:
        # Locks already held by caller
        for channel in channels.values():
            if nickname in channel:
                channel.discard(nickname)
                
        if nickname in clients:
            clients.pop(nickname, None)

# Helper function to handle client disconnect and other errors
def disconnectClient(nickname, locks_held=False):
    deleteUserdata(nickname, locks_held)
    print(f"{nickname} disconnected")

def checkClientConnection():
    while True:
        time.sleep(clientsCheckInterval)  # Check every 30 seconds
        currentTime = time.time()
        clientsToDisconnect = []
        
        with acquirelocks():
            for nickname, client_data in list(clients.items()):
                if currentTime - client_data['lastActivity'] > clientTimeout:
                    print(f"Client {nickname} timed out after {clientTimeout} seconds of inactivity")
                    clientsToDisconnect.append(nickname)
            
            # Disconnect inactive clients
            for nickname in clientsToDisconnect:
                currentChannel = getUsersChannel(nickname, True)
                if currentChannel:
                    broadcast(f"{nickname} has been disconnected due to inactivity", 
                              currentChannel, None, None, True)
                
                # Try to notify the client they're being disconnected
                try:
                    timestamp = datetime.now().strftime("%H.%M")
                    clients[nickname]['socket'].send(f"ERROR:{timestamp}:Disconnected due to inactivity".encode("utf-8"))
                    clients[nickname]['socket'].close()
                except:
                    pass
                
                disconnectClient(nickname, True)

# Function for broadcasting messages to all clients in a channel
def broadcast(message, channel, sender=None, clientSocket=None, locks_held=False):
    timestamp = datetime.now().strftime("%H.%M")
    if channel not in messageHistory:
        messageHistory[channel] = []
        
    messageEntry = {"sender": sender, "message": message, "time": timestamp}
    messageHistory[channel].append(messageEntry)
    
    if len(messageHistory[channel]) > MAX_HISTORY:
        messageHistory[channel] = messageHistory[channel][-MAX_HISTORY:]
    if not locks_held:
        with acquirelocks():
            if channel in channels:
                for nickname in channels[channel]:
                    if nickname != sender and nickname in clients:
                        try:
                            clients[nickname]['socket'].send(f"MSG:{timestamp}:{message}".encode("utf-8"))
                        except Exception as e:
                            print(f"Error sending to {nickname}: {e}")
                            # Direct modification since we're holding the locks
                            for ch in channels.values():
                                if nickname in ch:
                                    ch.discard(nickname)
                            if nickname in clients:
                                clients.pop(nickname, None)
    else:
        # Locks already held by caller
        if channel in channels:
            for nickname in channels[channel]:
                if nickname != sender and nickname in clients:
                    try:
                        clients[nickname]['socket'].send(f"MSG:{timestamp}:{message}".encode("utf-8"))
                    except Exception as e:
                        print(f"Error sending to {nickname}: {e}")
                        # Direct modification since we're holding the locks
                        for ch in channels.values():
                            if nickname in ch:
                                ch.discard(nickname)
                        if nickname in clients:
                            clients.pop(nickname, None)
    
    # Confirm to sender their message was sent (outside the lock)
    if sender and clientSocket:
        try:
            
            clientSocket.send(f"MSG_SENT:{timestamp}:{message}".encode("utf-8"))
        except Exception as e:
            print(f"Error confirming to sender: {e}")

# Function for sending private messages
def privatemessage(message, sender, receiver, clientSocket):
    timestamp = datetime.now().strftime("%H.%M")
    with clientsLock:
        actual_receiver = None
        for nick in clients:
            if nick.lower() == receiver.lower():
                actual_receiver = nick
                break
                
        if actual_receiver:
            try:
                clients[actual_receiver]['socket'].send(f"PRIVATE:{timestamp}:{sender}:{message}".encode("utf-8"))
                clientSocket.send(f"PRIVATE_SENT:{timestamp}:{actual_receiver}:{message}".encode("utf-8"))
                # Update last activity for receiver
                clients[actual_receiver]['lastActivity'] = time.time()
                return True
            except Exception as e:
                print(f"Error sending DM: {e}")
                timestamp = datetime.now().strftime("%H.%M")
                clientSocket.send(f"ERROR:{timestamp}:Failed to send message to {actual_receiver}".encode("utf-8"))
        else:
            timestamp = datetime.now().strftime("%H.%M")
            clientSocket.send(f"ERROR:{timestamp}:User {receiver} not found".encode("utf-8"))
    return False

# Function for handling client
def handleClient(clientSocket, clientAddress):
    # Get nickname from client
    nickname = None
    defaultChannel = "general"
    try:
        while not nickname:  # Get nickname from client
            msg = clientSocket.recv(1024).decode("utf-8")
            if not msg:
                return  # Client disconnected during nickname setup
                
            if msg.startswith("NICKNAME:"):
                requestNickname = msg.split("NICKNAME:",1)[1].strip()
                
                # Basic nickname validation
                if len(requestNickname) < 2 or len(requestNickname) > 20:
                    timestamp = datetime.now().strftime("%H.%M")
                    clientSocket.send(f"ERROR:{timestamp}:Nickname must be between 2-20 characters".encode("utf-8"))
                    continue
                
                with clientsLock:  # Check if nickname is already taken
                    nicknameTaken = False
                    for nick in clients:
                        if nick.lower() == requestNickname.lower():
                            nicknameTaken = True
                            break
                            
                    if nicknameTaken:
                        timestamp = datetime.now().strftime("%H.%M")
                        clientSocket.send(f"ERROR:{timestamp}:Nickname already taken".encode("utf-8"))
                    else:
                        # Store both original and lowercase version for easier lookup
                        clients[requestNickname] = {
                            'socket': clientSocket, 
                            'lastActivity': time.time(),
                        }
                        nickname = requestNickname
                        timestamp = datetime.now().strftime("%H.%M")
                        clientSocket.send(f"INFO:{timestamp}:Welcome {nickname}".encode("utf-8"))
                        print(f"{nickname} connected")
        
        # Now outside the while loop - only executes after nickname is set
        with acquirelocks():
            if defaultChannel not in channels:
                channels[defaultChannel] = set()
            channels[defaultChannel].add(nickname)
            broadcast(f"{nickname} has joined the {defaultChannel}", defaultChannel, None, None, True)
        
        while True:
            msg = clientSocket.recv(1024).decode("utf-8")
            if not msg:
                break
            
            # Update last activity time whenever a message is received
            with clientsLock:
                if nickname in clients:
                    clients[nickname]['lastActivity'] = time.time()
            
            if msg.startswith("JOIN:"):
                requestChannel = msg.split("JOIN:",1)[1].strip()
                with clientsLock:
                    with channelsLock:
                        currentChannel = getUsersChannel(nickname, True)
                        if currentChannel and currentChannel != requestChannel:
                            channels[currentChannel].discard(nickname)
                            # Notify current channel members that user left
                            broadcast(f"{nickname} has left the channel", currentChannel, None, None, True)
                        if requestChannel not in channels:
                            channels[requestChannel] = set()
                        channels[requestChannel].add(nickname)
                        broadcast(f"{nickname} has joined the channel {requestChannel}", requestChannel, None, None, True) # Notify other channel members

                        # Update the history sending part in handleClient
                        if requestChannel in messageHistory and len(messageHistory[requestChannel]) > 1:
                            timestamp = datetime.now().strftime("%H.%M")
                            
                            # Send a header to mark the beginning of history
                            clientSocket.send(f"INFO:{timestamp}:--- Begin History ---\n".encode("utf-8"))
                            
                            # Send each history entry
                            for entry in messageHistory[requestChannel]:
                                sendername = entry['sender'] if entry['sender'] else "Server"
                                msg_timestamp = entry.get('time', 'unknown')
                                clientSocket.send(f"HISTORY:{msg_timestamp}:{sendername}:{entry['message']}\n".encode("utf-8"))
                            
                            # Send a footer to mark the end of history
                            clientSocket.send(f"INFO:{timestamp}:--- End History ---\n".encode("utf-8"))
            elif msg.startswith("MSG:"):
                message = msg.split("MSG:",1)[1].strip()
                with clientsLock:
                    with channelsLock:
                        currentChannel = getUsersChannel(nickname, True)
                        if currentChannel:
                            broadcast(message, currentChannel, nickname, clientSocket, True)
                        else:
                            timestamp = datetime.now().strftime("%H.%M")
                            clientSocket.send(f"ERROR:{timestamp}:You are not in any channel".encode("utf-8"))   
            
            elif msg.startswith("LIST:"):
                listType = msg.split("LIST:",1)[1].strip()
                if listType == "CLIENTS" or listType == "clients":
                    with clientsLock:
                        clientlist = ", ".join(clients.keys())
                        # Remove timestamp from client list - it's not needed
                        clientSocket.send(f"CLIENTS:{clientlist}".encode("utf-8"))
                elif listType == "channels" or listType == "CHANNELS":
                    with channelsLock:
                        channellist = ", ".join(channels.keys())
                        # Remove timestamp from channel list - it's not needed
                        clientSocket.send(f"CHANNELS:{channellist}".encode("utf-8"))
                                              
            elif msg.startswith("DM:"):
                parts = msg.split("DM:",1)[1].split(":",1)
                if len(parts) == 2:
                    receiver = parts[0].strip()
                    content = parts[1].strip()
                    privatemessage(content, nickname, receiver, clientSocket)
                else:
                    timestamp = datetime.now().strftime("%H.%M")
                    clientSocket.send(f"ERROR:{timestamp}:Invalid DM format".encode("utf-8"))
                    
            elif msg.startswith("QUIT"):
                with acquirelocks():
                    currentChannel = getUsersChannel(nickname, True)
                    if currentChannel:
                        broadcast(f"{nickname} has left the channel", currentChannel, nickname, clientSocket, True)
                    disconnectClient(nickname, True) 
                clientSocket.close()
                break
                
    except Exception as e:
        print(f"Error handling client {clientAddress}: {e}")
    finally:
        if nickname: 
            with clientsLock:
                with channelsLock:
                    currentChannel = getUsersChannel(nickname, True)
                    if currentChannel:
                        broadcast(f"{nickname} has left the channel", currentChannel, nickname, None, True)
                    disconnectClient(nickname, True)
            try:
                clientSocket.close()
            except:
                pass
            print(f"Connection closed: {clientAddress}")

# Start server
if __name__ == "__main__":
    startServer()