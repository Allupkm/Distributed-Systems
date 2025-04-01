import socket
import threading
import os
import time



def connectToServer(address):
    try:
        if ":" in address:
            host, port_str = address.split(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                print(f"Invalid port number: {port_str}")
                return None
        else:
            host = "127.0.0.1"  # Default ip address
            port = 3000  # Default port
        
        # Create socket and connect
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((host, port))
        print(f"Connected to server at {host}:{port}")
        return clientSocket
        
    except socket.error as e:
        print(f"Error connecting to server: {e}")
        return None


#Function to clear the screen when changing channels
def clearScreen():
    # Clear the screen for windows
    if os.name == 'nt':
        os.system('cls')
    else: # Clear the screen for mac and linux
        os.system('clear')
    
# Function for joining a channel
def joinChannel(clientSocket, message): 
    try:
        clientSocket.send(f"JOIN:{message}".encode("utf-8")) # Send JOIN command to server
        print("Type your messages or use /help for available commands\n")
        return True
    except Exception as e: # Catch any errors and return False
        print(f"Error joining channel: {e}")
        return False
    
# Function for sending messages
def sendMessage(clientSocket, message):
    try:
        clientSocket.send(f"MSG:{message}".encode("utf-8")) # Send MSG command to server
        return True
    except Exception as e: # Catch any errors and return False
        print(f"Error sending message: {e}")
        return False
    
# Function for sending direct messages
def sendDirectMessage(clientSocket, recipient, message):
    try:
        clientSocket.send(f"DM:{recipient}:{message}".encode("utf-8")) # Send DM command
        return True
    except Exception as e: # Catch any errors and return False
        print(f"Error sending direct message: {e}")
        return False
    
# Function for listing channels and users
def listChannelsandClients(clientSocket, message):
    try:
        clientSocket.send(f"LIST:{message}".encode("utf-8")) # Send LIST command
        return True
    except Exception as e: # Catch any errors and return False
        print(f"Error listing clients or channels: {e}")
        return False

# Function for receiving messages from server
def receiveMessages(clientSocket, running_event):
    try:
        while running_event.is_set():
            try:
                message = clientSocket.recv(1024).decode("utf-8")
                if not message:
                    print("Connection to server lost")
                    running_event.clear()
                    return
                
                # For regular messages
                if message.startswith("MSG:"):
                    parts = message.split(":", 2)
                    if len(parts) >= 3:
                        timestamp = parts[1]
                        content = parts[2]
                        print(f"[{timestamp}] {content}")
                    else: #Fallback if something goes wrong
                        print(message[4:])
                
                # For sent message confirmation
                elif message.startswith("MSG_SENT:"):
                    parts = message.split(":", 2)
                    if len(parts) >= 3:
                        timestamp = parts[1]
                        content = parts[2]
                        print(f"[{timestamp}] Message sent: {content}")
                    else: #Fallback if something goes wrong
                        print(f"Message sent: {message[9:]}")
                
                # For private messages received
                elif message.startswith("PRIVATE:"):
                    parts = message.split(":", 3) # Split into 4 parts
                    if len(parts) >= 4:
                        timestamp = parts[1]
                        sender = parts[2]
                        content = parts[3]
                        print(f"[{timestamp}] DM from {sender}: {content}")
                    else:
                        #Fallback if something goes wrong
                        print(f"DM: {message[8:]}")
                
                # For private messages sent
                elif message.startswith("PRIVATE_SENT:"):
                    parts = message.split(":", 3)  # Split into 4 parts
                    if len(parts) >= 4:
                        timestamp = parts[1]
                        receiver = parts[2]
                        content = parts[3]
                        print(f"[{timestamp}] DM to {receiver}: {content}")
                    else: #Fallback if something goes wrong
                        print(f"DM sent: {message[13:]}")
                
                # For client list
                elif message.startswith("CLIENTS:"):
                    clients_list = message[8:]  # Just get everything after CLIENTS:
                    print(f"Online clients: {clients_list}")
                
                # For channel list
                elif message.startswith("CHANNELS:"):
                    channels_list = message[9:]  # Just get everything after CHANNELS:
                    print(f"Available channels: {channels_list}")
                
                # For info messages
                elif message.startswith("INFO:"):
                    parts = message.split(":", 2)
                    if len(parts) >= 3:
                        timestamp = parts[1]
                        info_message = parts[2]
                        print(f"[{timestamp}] {info_message}")
                    else:
                        print(message[5:])
                
                # For error messages
                elif message.startswith("ERROR:"):
                    parts = message.split(":", 2)
                    if len(parts) >= 3:
                        timestamp = parts[1]
                        error_message = parts[2]
                        print(f"[{timestamp}] Error: {error_message}")
                    else:
                        print(f"Error: {message[6:]}")
                
                # For server disconnect
                elif message.startswith("QUIT"):
                    print("Server disconnected")
                    running_event.clear()
                    return
                
                # For history messages
                elif message.startswith("HISTORY:"):
                    parts = message.split(":", 3)  # Split into 4 parts
                    if len(parts) >= 4:
                        timestamp = parts[1]
                        sender = parts[2]
                        content = parts[3]
                        # Display history message with timestamp and sender
                        print(f"[{timestamp}] {sender} (history): {content}\n")
                    else:
                        #Fallback if something goes wrong
                        print(f"History: {message[8:]}\n")
                
                # For any other message type
                else:
                    print(message)
                    
            except socket.error: # Handle socket error
                # Only show connection error if we're still supposed to be running
                if running_event.is_set():
                    print("Connection error")
                running_event.clear()
                return
                
    except Exception as e: # Catch any errors and clear the running event
        print(f"Error receiving messages: {e}")
        running_event.clear()

def helpmenu(): # Display help menu
    print("\nAvailable commands:")
    print("/join <channel> - Join a channel")
    print("/dm <client> <message> - Send a direct message to a user")
    print("/list channels - List available channels")
    print("/list clients - List online clients")
    print("/quit - Disconnect from the server")
    print("/help - Show help menu with available commands")
    print("Type your message and press Enter to send to the current channel\n")

def disconnect(clientSocket, running_event):
    print("Disconnecting from server...")
    try:
        # Clear the running event to stop receiving messages
        running_event.clear()
        # Give the receive thread a moment to notice the event is cleared
        time.sleep(0.1)
        
        # Only send QUIT if the socket is still valid
        try:
            clientSocket.send("QUIT".encode("utf-8"))
        except:
            # Socket may already be closed, that's okay
            pass
        
        try:
            clientSocket.close()
        except:
            # Socket may already be closed, that's okay
            pass
        
        print("Disconnected from server")
    except Exception as e: # Catch any errors during disconnect
        print(f"Error during disconnect: {e}")

def main():
    # Get server address
    server_input = input("Enter server address or press enter to use default (127.0.0.1:3000): ")
    
    # Use default if nothing entered
    if not server_input: 
        server_address = "127.0.0.1:3000"
    else:
        server_address = server_input
    
    # Connect to server
    clientSocket = connectToServer(server_address)
    if not clientSocket:
        return  # Exit if connection failed due to invalid address or other error
    
    nickname = None # Initialize nickname
    while not nickname or len(nickname) < 1:  # Loop until a valid nickname is set
        nickname = input("Enter your nickname: ").strip() # Get nickname from user
        if nickname:
            try:
                clientSocket.send(f"NICKNAME:{nickname}".encode("utf-8")) # Send nickname to server
                response = clientSocket.recv(1024).decode("utf-8") # Receive response from server
                if response.startswith("ERROR:"):
                    print(response) # Print error message if nickname is invalid
                    nickname = None
                else:
                    print(response) # Print success message if nickname is valid
            except Exception as e: # Catch any errors while setting nickname
                print(f"Error setting nickname: {e}") 
                return
    
    running_event = threading.Event() # Create an event to control the receive thread
    running_event.set() # Set the event to indicate that the thread should run
 
    receiveThread = threading.Thread(target=receiveMessages, args=(clientSocket, running_event)) # Create a thread for receiving messages
    receiveThread.daemon = True # Set the thread as a daemon so it will exit when the main program exits
    receiveThread.start() # Start the receive thread
    
    helpmenu()
    # Main loop for sending messages
    try:
        while running_event.is_set(): # Loop while the running event is set
            message = input().strip() # Get message from user
            if not message:
                continue
                
            if message.startswith("/"): # Check if the message is a command
                command = message[1:].split(" ", 1) # Split command and arguments
                cmd = command[0].upper() # Get command in uppercase to handle case insensitivity

                if cmd == "JOIN" and len(command) > 1: # Join a channel
                    channel = command[1]
                    # Clear screen before joining - makes history more readable
                    clearScreen()
                    joinChannel(clientSocket, channel) # Join the channel
                elif cmd == "DM" and len(command) > 1: # Send a direct message
                    dm_parts = command[1].split(" ", 1) # Split into recipient and message
                    if len(dm_parts) == 2:
                        sendDirectMessage(clientSocket, dm_parts[0], dm_parts[1]) # Send the direct message
                    else:
                        print("Invalid DM format. Use: /dm <client> <message>") # Print error message if format is invalid
                elif cmd == "LIST" and len(command) > 1: # List channels or clients
                    if command[1].upper() == "CHANNELS":
                        listChannelsandClients(clientSocket, "CHANNELS") # List channels
                    elif command[1].upper() == "CLIENTS":
                        listChannelsandClients(clientSocket, "CLIENTS") # List clients
                    else:
                        print("Invalid list command. Use: /list channels or /list clients") # Print error message if command is invalid
                elif cmd == "QUIT": # Disconnect from server
                    disconnect(clientSocket, running_event)
                elif cmd == "HELP": # Show help menu
                    helpmenu()
                else:
                    print("Invalid command. Type /HELP for a list of commands") # Print error message if command is invalid

            else: # Regular message to send to the current channel
                sendMessage(clientSocket, message)
    except Exception as e: # Catch any errors and disconnect from server
        print(f"Error while running client: {e}")
        running_event.clear()
    finally: # Disconnect from server and close socket in any case to be sure that the socket is closed
        if running_event.is_set():
            disconnect(clientSocket, running_event)

main() # Runs main function
