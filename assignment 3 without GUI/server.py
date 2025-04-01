import socket
import threading
import time
from contextlib import contextmanager
from datetime import datetime

# Server configuration values change as needed
HOST = '0.0.0.0' # Bind to all interfaces
PORT = 3000
SERVERADDRESS = (HOST, PORT) # Server address and port
# Function to get local IP address
def get_local_ip():
    try:
        # Create a socket connection to an external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't actually connect but helps determine the interface
        s.connect(("8.8.8.8", 80))  
        ip = s.getsockname()[0] # Get local IP address
        s.close()
        return ip
    except Exception:
        return "Could not determine local IP. Try 'ipconfig' on Windows or 'ifconfig' on Linux/Mac" # Fallback message


# Values for checking client connection
clientTimeout = 120 # Timeout in seconds
clientsCheckInterval = 30 # Interval in seconds to check for client connection

# message history
messageHistory = {} # Store message history for each channel
MAX_HISTORY = 20 # Maximum number of messages to store

# Context manager for acquiring locks
@contextmanager
def acquirelocks(): # Acquire both locks
    with clientsLock:
        with channelsLock:
            yield

# Store clients using their nicknames
clients = {} # To store nickname, client sockets and last activity time
clientsLock = threading.Lock() # Lock for clients to be safe for concurrent access
 
# Store channels and their clients
channels = {"general": set()} # Store channels and their clients
channelsLock = threading.Lock() # Lock for channels to be safe for concurrent access

# Function for starting server
def startServer():
    # Create a socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP socket
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Reuse the socket
    serverSocket.bind(SERVERADDRESS) # Bind to the address
    serverSocket.listen() # Listen for connections
    serverSocket.settimeout(1) # Set a timeout for the socket to avoid blocking
    local_ip = get_local_ip() # Get local IP address for clients to connect in the network
    print("Server is starting...")
    print(f"Server started and listening on all interfaces (0.0.0.0:{PORT})")
    print(f"For clients to connect on your network, use this address: {local_ip}:{PORT}") #Display the local IP address
    print(f"For local connections, use: 127.0.0.1:{PORT}") # Display the local loopback address
    print("Press Ctrl+C to stop the server")
    # Start the client connection checker thread
    connectionCheckerThread = threading.Thread(target=checkClientConnection) 
    connectionCheckerThread.daemon = True # Daemonize the thread
    connectionCheckerThread.start() # Start the thread
    
    try:
        while True:
            try:
                # Wait for a connection
                clientSocket, clientAddress = serverSocket.accept()
                print(f"Connection from {clientAddress}")
                clientThread = threading.Thread(target=handleClient, args=(clientSocket, clientAddress)) # Create a new thread for the client
                clientThread.daemon = True # Daemonize the thread
                clientThread.start()
            except socket.timeout:
                #To allow KeyboardInterrupt to be caught
                # without blocking the server
                continue
    except KeyboardInterrupt:
        for client in clients.values(): # Notify all clients that the server is shutting down
            try:
                timestamp = datetime.now().strftime("%H.%M") # Get the current time
                client['socket'].send(f"ERROR:{timestamp}:Server is shutting down".encode("utf-8")) # Notify the client
                client['socket'].close() # Close the socket
            except:
                pass # Ignore errors while closing sockets
        serverSocket.close() # Close the server socket
        print("Server stopped") # Print server stopped message

# Helper functions for getting clients channel
def getUsersChannel(nickname, lockalreadyused=False):
    if not lockalreadyused: # Acquire the locks if not already held
        with channelsLock:
            for channel, users in channels.items():
                if nickname in users: 
                    return channel # Return the channel if the user is in it
    else:
        # If lock is already held, don't try to acquire it again
        for channel, users in channels.items():
            if nickname in users:
                return channel
    return None
# Helper functions for deleting userdata
def deleteUserdata(nickname, locks_held=False):
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
        # Locks already held
        for channel in channels.values():
            if nickname in channel:
                channel.discard(nickname)
                
        if nickname in clients: # Remove from clients dictionary
            clients.pop(nickname, None)

# Helper function to handle client disconnect and other errors
def disconnectClient(nickname, locks_held=False):
    deleteUserdata(nickname, locks_held) # Delete user data
    print(f"{nickname} disconnected")

def checkClientConnection():
    while True:
        time.sleep(clientsCheckInterval)  # Check every 30 seconds
        currentTime = time.time()  # Get the current time
        clientsToDisconnect = [] # List of clients to disconnect
        
        with acquirelocks(): 
            for nickname, client_data in list(clients.items()): # Iterate over a copy of the dictionary
                if currentTime - client_data['lastActivity'] > clientTimeout: # Check if the client has timed out
                    print(f"Client {nickname} timed out after {clientTimeout} seconds of inactivity") 
                    clientsToDisconnect.append(nickname)
            
            # Disconnect inactive clients
            for nickname in clientsToDisconnect: 
                currentChannel = getUsersChannel(nickname, True)
                if currentChannel:
                    broadcast(f"{nickname} has been disconnected due to inactivity", 
                              currentChannel, None, None, True)
                try: # Try to send a message to the client about the disconnection
                    timestamp = datetime.now().strftime("%H.%M") 
                    clients[nickname]['socket'].send(f"ERROR:{timestamp}:Disconnected due to inactivity".encode("utf-8"))
                    #clients[nickname]['socket'].close() # Close the socket reduntant since we are already disconnecting the client
                except:
                    pass
                
                disconnectClient(nickname, True) # Disconnect the client and remove from clients dictionary

# Function for broadcasting messages to all clients in a channel
def broadcast(message, channel, sender=None, clientSocket=None, locks_held=False): # Broadcast a message to all clients in a channel, Different messages depending on the sender
    timestamp = datetime.now().strftime("%H.%M")
    if channel not in messageHistory: # Create a new message history for the channel if it doesn't exist for channel
        messageHistory[channel] = []
        
    messageEntry = {"sender": sender, "message": message, "time": timestamp} # Create a message entry
    messageHistory[channel].append(messageEntry) # Store the message in the history
    
    if len(messageHistory[channel]) > MAX_HISTORY: # Limit the number of messages stored
        messageHistory[channel] = messageHistory[channel][-MAX_HISTORY:]
    if not locks_held:
        with acquirelocks():
            if channel in channels:
                for nickname in channels[channel]: # Iterate over all clients in the channel
                    if nickname != sender and nickname in clients: # Don't send the message to the sender
                        try:
                            clients[nickname]['socket'].send(f"MSG:{timestamp}:{message}".encode("utf-8")) 
                        except Exception as e:
                            print(f"Error sending to {nickname}: {e}")
                            # Direct modification since we're holding the locks
                            for ch in channels.values(): # Remove the client from all channels if they can't be reached
                                if nickname in ch:
                                    ch.discard(nickname)
                            if nickname in clients:  # Remove the client from the clients dictionary
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
                        for ch in channels.values(): # Remove the client from all channels if they can't be reached
                            if nickname in ch:
                                ch.discard(nickname)
                        if nickname in clients: # Remove the client from the clients dictionary
                            clients.pop(nickname, None)
    
    # Confirm to sender their message was sent (outside the lock)
    if sender and clientSocket:
        try:
            clientSocket.send(f"MSG_SENT:{timestamp}:{message}".encode("utf-8")) # Confirm to sender their message was sent
        except Exception as e:
            print(f"Error confirming to {sender}: {e}") #debugging line

# Function for sending private messages
def privatemessage(message, sender, receiver, clientSocket):
    timestamp = datetime.now().strftime("%H.%M")
    with clientsLock:
        actual_receiver = None # Actual receiver nickname
        for nick in clients:
            if nick.lower() == receiver.lower(): # Check if the receiver exists using case insensitive comparison
                actual_receiver = nick 
                break
                
        if actual_receiver:
            try:
                clients[actual_receiver]['socket'].send(f"PRIVATE:{timestamp}:{sender}:{message}".encode("utf-8")) # Send the private message
                clientSocket.send(f"PRIVATE_SENT:{timestamp}:{actual_receiver}:{message}".encode("utf-8"))
                # Update last activity for receiver
                clients[actual_receiver]['lastActivity'] = time.time()
                return True
            except Exception as e:
                print(f"Error sending DM: {e}")
                timestamp = datetime.now().strftime("%H.%M")
                clientSocket.send(f"ERROR:{timestamp}:Failed to send message to {actual_receiver}".encode("utf-8")) # Notify sender of failure
        else:
            timestamp = datetime.now().strftime("%H.%M")
            clientSocket.send(f"ERROR:{timestamp}:User {receiver} not found".encode("utf-8")) # Notify sender that the user was not found
    return False

# Function for handling client
def handleClient(clientSocket, clientAddress):
    nickname = None
    disconnetionCheck = False # Flag to check if the client is disconnected
    defaultChannel = "general" # Default channel for new clients
    try:
        while not nickname:  # Get nickname from client
            msg = clientSocket.recv(1024).decode("utf-8")
            if not msg:
                return  # Client disconnected during nickname setup
            if msg.startswith("NICKNAME:"):
                requestNickname = msg.split("NICKNAME:",1)[1].strip()
                
                # Basic nickname validation
                if len(requestNickname) < 2 or len(requestNickname) > 20: # Check if the nickname is between 2-20 characters
                    timestamp = datetime.now().strftime("%H.%M")
                    clientSocket.send(f"ERROR:{timestamp}:Nickname must be between 2-20 characters".encode("utf-8"))
                    continue
                
                with clientsLock:  # Check if nickname is already taken
                    nicknameTaken = False
                    for nick in clients: 
                        if nick.lower() == requestNickname.lower(): # Check if the nickname is already taken
                            nicknameTaken = True
                            break
                            
                    if nicknameTaken: # Notify client that the nickname is already taken
                        timestamp = datetime.now().strftime("%H.%M")
                        clientSocket.send(f"ERROR:{timestamp}:Nickname already taken".encode("utf-8"))
                    else:
                        # Add client to clients dictionary
                        clients[requestNickname] = {
                            'socket': clientSocket, 
                            'lastActivity': time.time(),
                        }
                        nickname = requestNickname # Set the nickname
                        timestamp = datetime.now().strftime("%H.%M")
                        clientSocket.send(f"INFO:{timestamp}:Welcome {nickname}".encode("utf-8"))
                        print(f"{nickname} connected")
        
        # Add client to default channel
        with acquirelocks():
            if defaultChannel not in channels:
                channels[defaultChannel] = set()
            channels[defaultChannel].add(nickname)
            broadcast(f"{nickname} has joined the {defaultChannel}", defaultChannel, None, None, True) # Notify other channel members doesn't need to send back msg_sent since it is not a message
        
        while True:
            msg = clientSocket.recv(1024).decode("utf-8") # Receive messages from the client
            if not msg:
                break
            
            # Update last activity time whenever a message is received
            with clientsLock:
                if nickname in clients:
                    clients[nickname]['lastActivity'] = time.time()
            # Handle different message types
            if msg.startswith("JOIN:"): # Join a channel
                requestChannel = msg.split("JOIN:",1)[1].strip()
                with clientsLock: 
                    with channelsLock:
                        currentChannel = getUsersChannel(nickname, True) # Get the current channel of the user
                        if currentChannel and currentChannel != requestChannel: # Check if the user is already in a channel
                            channels[currentChannel].discard(nickname)
                            # Notify current channel members that user left
                            broadcast(f"{nickname} has left the channel", currentChannel, None, None, True) # Notify other channel members doesn't need to send back msg_sent since it is not a message
                        if requestChannel not in channels: # Create the channel if it doesn't exist
                            channels[requestChannel] = set()
                        channels[requestChannel].add(nickname)
                        broadcast(f"{nickname} has joined the channel {requestChannel}", requestChannel, None, None, True) # Notify other channel members doesn't need to send back msg_sent since it is not a message

                        # Update the history sending part in handleClient and its not the first notify message
                        if requestChannel in messageHistory and len(messageHistory[requestChannel]) > 1:
                            timestamp = datetime.now().strftime("%H.%M")
                            
                            # Send a header to mark the beginning of history
                            clientSocket.send(f"INFO:{timestamp}:--- Begin History ---\n".encode("utf-8"))
                            
                            # Send each history entry
                            for entry in messageHistory[requestChannel]:
                                if entry['sender'] == nickname:
                                    sendername = "You"
                                else:
                                    sendername = entry.get('sender', 'Server') # Get the sender name or default to 'Server'
                                msg_timestamp = entry.get('time', 'unknown') # Get the message timestamp or default to 'unknown'
                                clientSocket.send(f"HISTORY:{msg_timestamp}:{sendername}:{entry['message']}\n".encode("utf-8"))
                            
                            # Send a footer to mark the end of history
                            clientSocket.send(f"INFO:{timestamp}:--- End History ---\n".encode("utf-8"))
            elif msg.startswith("MSG:"): # Send a message to the channel
                message = msg.split("MSG:",1)[1].strip() # Check if the message is in the correct format
                with clientsLock:
                    with channelsLock:
                        currentChannel = getUsersChannel(nickname, True) # Get the current channel of the user
                        if currentChannel:
                            broadcast(message, currentChannel, nickname, clientSocket, True) # Broadcast the message to the channel and send confirmation to the sender
                        else:
                            timestamp = datetime.now().strftime("%H.%M") # Notify the client that they are not in any channel
                            clientSocket.send(f"ERROR:{timestamp}:You are not in any channel".encode("utf-8")) #   
            
            elif msg.startswith("LIST:"): # List clients or channels
                listType = msg.split("LIST:",1)[1].strip()
                if listType == "CLIENTS" or listType == "clients":  # List clients
                    with clientsLock:
                        clientlist = ", ".join(clients.keys())
                        clientSocket.send(f"CLIENTS:{clientlist}".encode("utf-8"))
                elif listType == "channels" or listType == "CHANNELS": # List channels
                    with channelsLock:
                        channellist = ", ".join(channels.keys())
                        clientSocket.send(f"CHANNELS:{channellist}".encode("utf-8"))
                                              
            elif msg.startswith("DM:"): # Send a private message
                parts = msg.split("DM:",1)[1].split(":",1)
                if len(parts) == 2: # Check if the message is in the correct format
                    receiver = parts[0].strip()
                    content = parts[1].strip()
                    privatemessage(content, nickname, receiver, clientSocket) # Send the private message
                else:
                    timestamp = datetime.now().strftime("%H.%M")
                    clientSocket.send(f"ERROR:{timestamp}:Invalid DM format".encode("utf-8")) # Notify the client of the invalid format
                    
            elif msg.startswith("QUIT"): # Disconnect the client
                with acquirelocks():
                    currentChannel = getUsersChannel(nickname, True)
                    if currentChannel:
                        broadcast(f"{nickname} has left the channel", currentChannel, nickname, None, True) # Notify other channel members doesn't need to send back msg_sent since it is not a message
                    disconnectClient(nickname, True)  # Disconnect the client
                    disconnetionCheck = True # Set the disconnection check flag to true
                clientSocket.close()
                break
                
    except Exception as e:
        print(f"Error handling client {clientAddress}: {e}") # Print the error
    finally: # Disconnect the client and close the socket if an error occurs and to be sure that client is disconnected
        if nickname and not disconnetionCheck: # Check if the nickname is set and the client is not already disconnected
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
startServer()
