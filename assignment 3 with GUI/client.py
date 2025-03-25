import socket
import threading
import os
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog, messagebox

class ConnectDialog:
    def __init__(self, parent, title, default_server="127.0.0.1:3000", default_nickname=""):
        self.result = None
        
        # Create top level dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # Center dialog
        window_width = 300
        window_height = 150
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create frame with padding
        frame = ttk.Frame(self.dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Server address
        ttk.Label(frame, text="Server address:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.server_var = tk.StringVar(value=default_server)
        self.server_entry = ttk.Entry(frame, width=30, textvariable=self.server_var)
        self.server_entry.grid(row=0, column=1, pady=5, padx=5)
        
        # Nickname
        ttk.Label(frame, text="Nickname:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.nickname_var = tk.StringVar(value=default_nickname)
        self.nickname_entry = ttk.Entry(frame, width=30, textvariable=self.nickname_var)
        self.nickname_entry.grid(row=1, column=1, pady=5, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Connect", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        # Set focus and wait for dialog
        self.server_entry.focus_set()
        self.dialog.wait_window()
        
    def ok(self):
        self.result = (self.server_var.get(), self.nickname_var.get())
        self.dialog.destroy()
        
    def cancel(self):
        self.dialog.destroy()

class ChatClientGUI: # Main class for the chat client GUI
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Client")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.clientSocket = None # Socket for client
        self.running_event = threading.Event() # Event for running state
        self.currentChannel = None # Current channel
        
        # Store last connection details for reconnection
        self.last_server = None 
        self.last_nickname = None
        
        # Create the chat frame
        self.createChatFrame()
        
    def createChatFrame(self):
        # Remove existing frame if it exists
        for widget in self.root.winfo_children():
            widget.destroy()
        # Create the chat frame
        self.chatFrame = ttk.Frame(self.root, padding=10)
        self.chatFrame.pack(fill=tk.BOTH, expand=True)
        
        # Top frame for status and channel info
        topFrame = ttk.Frame(self.chatFrame)
        topFrame.pack(fill=tk.X, pady=5)
        
        # Status label
        self.statusLabel = ttk.Label(topFrame, text="Not connected")
        self.statusLabel.pack(side=tk.LEFT)
        
        # Channel label
        self.channelLabel = ttk.Label(topFrame, text="No channel")
        self.channelLabel.pack(side=tk.RIGHT)
        
        # Chat area
        self.chatArea = scrolledtext.ScrolledText(self.chatFrame, wrap=tk.WORD, width=80, height=25)
        self.chatArea.pack(fill=tk.BOTH, expand=True, pady=5)

        # Configure the text tags
        self.chatArea.tag_configure("black", foreground="black")
        self.chatArea.tag_configure("blue", foreground="blue")  
        self.chatArea.tag_configure("red", foreground="red")
        self.chatArea.tag_configure("green", foreground="green")
        self.chatArea.tag_configure("gray", foreground="gray")
        self.chatArea.tag_configure("purple", foreground="purple")
        self.chatArea.tag_configure("orange", foreground="orange")

        self.chatArea.config(state=tk.DISABLED) # Disable editing
        
        # Create input area
        inputFrame = ttk.Frame(self.chatFrame)
        inputFrame.pack(fill=tk.X, pady=5)
        # Message entry
        self.messageEntry = ttk.Entry(inputFrame, width=70)
        self.messageEntry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.messageEntry.bind("<Return>", lambda e: self.sendMessage())
        # Send button
        sendButton = ttk.Button(inputFrame, text="Send", command=self.sendMessage)
        sendButton.pack(side=tk.LEFT, padx=5)
        
        buttonFrame = ttk.Frame(self.chatFrame)
        buttonFrame.pack(fill=tk.X, pady=5)
        
        # First row of buttons
        buttonRow1 = ttk.Frame(buttonFrame)
        buttonRow1.pack(fill=tk.X, pady=2)
        
        # Combined Connect/Disconnect button
        self.connectButton = ttk.Button(buttonRow1, text="Connect", command=self.toggleConnection)
        self.connectButton.pack(side=tk.LEFT, padx=2)
        
        # Other buttons in the first row
        ttk.Button(buttonRow1, text="Join Channel", command=self.joinchannel).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttonRow1, text="Direct Message", command=self.directmessage).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttonRow1, text="List Channels", command=lambda: self.listchannelsandclients("CHANNELS")).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttonRow1, text="List Users", command=lambda: self.listchannelsandclients("CLIENTS")).pack(side=tk.LEFT, padx=2)
        
        # Second row with just Help button
        buttonRow2 = ttk.Frame(buttonFrame)
        buttonRow2.pack(fill=tk.X, pady=2)
        
        ttk.Button(buttonRow2, text="Help", command=self.showhelp).pack(side=tk.LEFT, padx=2)

        # Show a welcome message
        self.addMessage("Welcome to the Chat Client!", "purple")
        self.addMessage("Click 'Connect' to join a server.", "purple")
        
    def showConnectDialog(self):
        # If already connected, ask to disconnect first
        if self.clientSocket and self.running_event.is_set():
            if messagebox.askyesno("Already Connected", "You are already connected. Disconnect and connect to a new server?"):
                self.disconnect()
            else:
                return
            
        # Default values for the dialog
        default_server = self.last_server if self.last_server else "127.0.0.1:3000"
        default_nickname = self.last_nickname if self.last_nickname else ""
        
        # Show the connection dialog
        dialog = ConnectDialog(self.root, "Connect to Server", default_server, default_nickname)
        
        if dialog.result: # 
            server_address, nickname = dialog.result
            if not server_address:
                server_address = "127.0.0.1:3000"
            if not nickname:
                messagebox.showwarning("Error", "Please enter a nickname")
                return
                
            self.connectToServer(server_address, nickname)
        
    def connectToServer(self, serverAddress, nickname):
        # Store connection details for potential reconnection
        self.last_server = serverAddress
        self.last_nickname = nickname
        
        # Continue with connection process
        try:
            if ":" in serverAddress:
                host, port_str = serverAddress.split(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    messagebox.showwarning("Error", f"Invalid port number: {port_str}")
                    return
            else:
                host = serverAddress
                port = 3000
                
            self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create socket
            self.clientSocket.connect((host, port)) # Connect to server
            self.clientSocket.send(f"NICKNAME:{nickname}".encode("utf-8")) # Send nickname to server
            response = self.clientSocket.recv(1024).decode("utf-8") # Receive response from server
            
            if response.startswith("ERROR:"): # If error, show error message and close socket
                messagebox.showwarning("Error", response)
                self.clientSocket.close()
                self.clientSocket = None
                return
            
            # Now we can update the status label
            self.statusLabel.config(text=f"Connected as {nickname}")
            self.running_event.set()
            self.connectButton.config(text="Disconnect")  # Change button to Disconnect
            
            # Start receive thread
            receiveThread = threading.Thread(target=self.receiveMessages)
            receiveThread.daemon = True
            receiveThread.start()
            
            # Add welcome message
            self.clearChat()  # Clear chat window first
            self.addMessage(f"Connected to server. {response}")
            self.addMessage("Type your messages or use the buttons for commands")
            
        except Exception as e: # Handle connection errors
            messagebox.showwarning("Error", f"Error connecting to server: {e}")
            if self.clientSocket:
                self.clientSocket.close()
                self.clientSocket = None
            return
            
    def clearChat(self): # Clear chat area
        self.chatArea.config(state=tk.NORMAL)
        self.chatArea.delete(1.0, tk.END)
        self.chatArea.config(state=tk.DISABLED)
        
    # Add message method to handle different colors
    def addMessage(self, message, color="black"):
        self.chatArea.config(state=tk.NORMAL)
        
        # Map color names to hex values for more reliable coloring
        color_map = {
            "black": "#000000",
            "blue": "#0000FF",
            "red": "#FF0000",
            "green": "#008000",
            "gray": "#808080",
            "purple": "#800080",
            "orange": "#FFA500"
        }
        
        # Get the hex color
        hex_color = color_map.get(color, "#000000")
        
        # Create a unique tag name for this message
        tag_name = f"color_{self.chatArea.index(tk.END).replace('.', '_')}"
        
        # Insert the message
        self.chatArea.insert(tk.END, message + "\n", tag_name)
        
        # Configure the tag with the color
        self.chatArea.tag_configure(tag_name, foreground=hex_color)
        
        self.chatArea.config(state=tk.DISABLED)
        self.chatArea.see(tk.END)
        
    def sendMessage(self): # Send message to server
        if not self.clientSocket or not self.running_event.is_set(): # If not connected, show warning
            messagebox.showwarning("Error", "Not connected to server")
            return
            
        message = self.messageEntry.get().strip() # Get message from entry
        if not message:
            return
            
        try:
            # Handle special commands
            if message.startswith("/"):
                parts = message[1:].split(" ", 1)
                command = parts[0].lower()
                
                if command == "join" and len(parts) > 1: # Join channel
                    channel = parts[1].strip()
                    self.clientSocket.send(f"JOIN:{channel}".encode("utf-8"))
                    self.currentChannel = channel
                    self.channelLabel.config(text=f"Channel: {channel}")
                    self.clearChat()  # Clear chat when joining new channel
                
                elif command == "dm" and len(parts) > 1: # Direct message
                    dm_parts = parts[1].split(" ", 1)
                    if len(dm_parts) < 2:
                        self.addMessage("Usage: /dm <nickname> <message>", "red")
                    else:
                        recipient = dm_parts[0].strip() # Get recipient
                        dm_message = dm_parts[1].strip()
                        self.clientSocket.send(f"DM:{recipient}:{dm_message}".encode("utf-8"))
                
                elif command == "list" and len(parts) > 1: # List channels or clients
                    list_type = parts[1].strip().upper()
                    self.clientSocket.send(f"LIST:{list_type}".encode("utf-8"))
                
                elif command == "quit": # Disconnect
                    self.disconnect()
                
                else: # Unknown command
                    self.addMessage(f"Unknown command: {command}", "red")
            else:
                # Format message to include sender name for better channel display
                formatted_message = f"{self.last_nickname}: {message}"
                self.clientSocket.send(f"MSG:{formatted_message}".encode("utf-8"))
                
            self.messageEntry.delete(0, tk.END) # Clear message entry
        except Exception as e:
            self.addMessage(f"Error sending message: {e}", "red") # Show error message
            
    def joinchannel(self): # Join a channel
        if not self.clientSocket or not self.running_event.is_set():
            messagebox.showwarning("Error", "Not connected to server")
            return
            
        channel = simpledialog.askstring("Join Channel", "Enter channel name:") # Get channel name
        if channel:
            try:
                self.clientSocket.send(f"JOIN:{channel}".encode("utf-8")) # Send JOIN command to server
                self.currentChannel = channel 
                self.channelLabel.config(text=f"Channel: {channel}")
                self.clearChat()  # Clear chat when joining new channel
            except Exception as e:
                self.addMessage(f"Error joining channel: {e}", "red")
                
    def directmessage(self): # Send a direct message
        if not self.clientSocket or not self.running_event.is_set(): # If not connected, show warning
            messagebox.showwarning("Error", "Not connected to server")
            return
            
        recipient = simpledialog.askstring("Direct Message", "Enter recipient's nickname:") # Get recipient
        if not recipient:
            return
            
        message = simpledialog.askstring("Direct Message", f"Enter message for {recipient}:") # Get message
        if message:
            try:
                self.clientSocket.send(f"DM:{recipient}:{message}".encode("utf-8")) # Send DM command to server
            except Exception as e:
                self.addMessage(f"Error sending direct message: {e}", "red") # Show error message
                
    def listchannelsandclients(self, list_type): # List channels or clients
        if not self.clientSocket or not self.running_event.is_set(): # If not connected, show warning
            messagebox.showwarning("Error", "Not connected to server")
            return
            
        try:
            self.clientSocket.send(f"LIST:{list_type}".encode("utf-8")) # Send LIST command to server
        except Exception as e:
            self.addMessage(f"Error listing {list_type}: {e}", "red") # Show error message
            
    def showhelp(self): # Show help message
        help_text = """
Available Commands:
- Connect: Connect to a chat server
- Join Channel: Join a specific channel
- Direct Message: Send a private message to a specific user
- List Channels: Show all available channels
- List Users: Show all connected users
- Help: Display this help message
- Disconnect: Disconnect from the server

You can also type commands directly in the message input:
/join <channel> - Join a channel
/dm <client> <message> - Send a direct message
/list channels - List available channels
/list clients - List online clients
/quit - Disconnect from the server
        """
        messagebox.showinfo("Help", help_text) # Show help message
        
    def disconnect(self): # Disconnect from server
        if not self.clientSocket or not self.running_event.is_set(): # If not connected, show warning
            return   
        try:
            self.running_event.clear()
            time.sleep(0.1)     # Wait for receive thread to finish
            try:
                self.clientSocket.send("QUIT".encode("utf-8")) # Send QUIT command to server
            except:
                pass        
            try:
                self.clientSocket.close() # Close socket
            except:
                pass    
            self.clientSocket = None # Reset socket
            self.addMessage("Disconnected from server") # Show disconnection message
            self.statusLabel.config(text="Disconnected") # Update status label
            self.channelLabel.config(text="No channel") # Update channel label
            self.connectButton.config(text="Connect")  # Change button back to Connect
        except Exception as e:
            self.addMessage(f"Error during disconnect: {e}", "red") # Show error message
            
    def receiveMessages(self): # Receive messages from server
        try:
            while self.running_event.is_set(): # While running
                try:
                    message = self.clientSocket.recv(1024).decode("utf-8") # Receive message from server
                    if not message: # If no message
                        self.addMessage("Connection to server lost", "red") 
                        self.running_event.clear()
                        self.statusLabel.config(text="Disconnected") # Update status label
                        self.connectButton.config(text="Connect") # Change button back to Connect
                        self.clientSocket = None
                        return        
                    
                    # Process different message types
                    if message.startswith("MSG:"): # Regular message 
                        parts = message.split(":", 2)
                        if len(parts) >= 3:
                            timestamp = parts[1]
                            content = parts[2]
                            
                            # System messages or notifications
                            if "joined the channel" in content or "left the channel" in content or content.startswith("Server:"):
                                self.addMessage(f"[{timestamp}] {content}", "purple")
                            else:
                                # Try to parse sender from content
                                content_parts = content.split(": ", 1)
                                if len(content_parts) >= 2:
                                    sender = content_parts[0]
                                    actual_content = content_parts[1]
                                    
                                    # If this is a message from the current user, show in green
                                    if sender == self.last_nickname:
                                        self.addMessage(f"[{timestamp}] {sender}: {actual_content}", "green")
                                    else:
                                        # Messages from others are black by default
                                        self.addMessage(f"[{timestamp}] {sender}: {actual_content}")
                                else:
                                    # Regular channel message
                                    self.addMessage(f"[{timestamp}] {content}")
                        else:
                            self.addMessage(message[4:]) # Regular message
                     
                    elif message.startswith("MSG_SENT:"): # Message sent confirmation
                        parts = message.split(":", 2)
                        if len(parts) >= 3:
                            timestamp = parts[1]
                            content = parts[2]
                            # Messages you sent should be green
                            self.addMessage(f"[{timestamp}] {content}", "green")
                        else:
                            self.addMessage(f"Message sent: {message[9:]}", "green")
                    
                    elif message.startswith("PRIVATE:"): # Private message
                        parts = message.split(":", 3)
                        if len(parts) >= 4:
                            timestamp = parts[1]
                            sender = parts[2]
                            content = parts[3]
                            self.addMessage(f"[{timestamp}] DM from {sender}: {content}", "blue")
                        else:
                            self.addMessage(f"DM: {message[8:]}", "blue")
                    
                    elif message.startswith("PRIVATE_SENT:"): # Private message sent confirmation
                        parts = message.split(":", 3)
                        if len(parts) >= 4:
                            timestamp = parts[1]
                            receiver = parts[2]
                            content = parts[3]
                            self.addMessage(f"[{timestamp}] DM to {receiver}: {content}", "green")
                        else:
                            self.addMessage(f"DM sent: {message[13:]}", "green")
                    
                    elif message.startswith("CLIENTS:"): # Online clients list
                        clients_list = message[8:]
                        self.addMessage(f"Online clients: {clients_list}", "purple")
                    
                    elif message.startswith("CHANNELS:"): # Available channels list
                        channels_list = message[9:]
                        self.addMessage(f"Available channels: {channels_list}", "purple")
                    
                    elif message.startswith("INFO:"): # Information message
                        parts = message.split(":", 2)
                        if len(parts) >= 3:
                            timestamp = parts[1]
                            info_message = parts[2]
                            self.addMessage(f"[{timestamp}] Info: {info_message}", "orange")
                        else:
                            self.addMessage(message[5:], "orange")
                    
                    elif message.startswith("ERROR:"): # Error message
                        parts = message.split(":", 2) 
                        if len(parts) >= 3:
                            timestamp = parts[1]
                            error_message = parts[2]
                            
                            # Display the error message
                            self.addMessage(f"[{timestamp}] Error: {error_message}", "red")
                            
                            # Special handling for inactivity disconnect
                            if "inactivity" in error_message.lower():
                                # Show a clear message about inactivity
                                self.addMessage("You were disconnected due to inactivity. Use Connect to reconnect.", "red")
                                # Process disconnect after giving UI time to update
                                self.root.after(500, self.handleInactivityDisconnect)
                        else:
                            self.addMessage(f"Error: {message[6:]}", "red")
                    
                    elif message.startswith("QUIT"): # Server quit message
                        self.addMessage("Server disconnected", "red")
                        self.running_event.clear()
                        self.statusLabel.config(text="Disconnected")
                        self.connectButton.config(text="Connect")
                        return
                    
                    elif message.startswith("HISTORY:"): # History message
                        parts = message.split(":", 3)
                        if len(parts) >= 4:
                            timestamp = parts[1]
                            sender = parts[2]
                            content = parts[3]
                            # Properly display the sender for history messages
                            self.addMessage(f"[{timestamp}] {sender}: {content}", "gray")
                        else:
                            self.addMessage(f"History: {message[8:]}", "gray")
                    
                    elif message.startswith("JOIN:"): # Channel joining message
                        parts = message.split(":", 2)
                        if len(parts) >= 3:
                            channel = parts[2]
                            self.currentChannel = channel
                            self.channelLabel.config(text=f"Channel: {channel}")
                            # Highlight channel joining
                            self.addMessage(f"Joined channel: {channel}", "purple")
                    else:
                        # Generic messages (shouldn't normally reach here)
                        self.addMessage(message)
                        
                except socket.error: # Handle socket errors
                    if self.running_event.is_set():
                        self.addMessage("Connection error", "red")
                    self.running_event.clear()
                    self.statusLabel.config(text="Disconnected")
                    self.connectButton.config(text="Connect")
                    return
                    
        except Exception as e: # Handle general errors
            self.addMessage(f"Error receiving messages: {e}", "red")
            self.running_event.clear()
            self.statusLabel.config(text="Disconnected")
            self.connectButton.config(text="Connect")

    def handleInactivityDisconnect(self):
        # Ensure we're still connected before trying to disconnect
        if self.clientSocket and self.running_event.is_set():
            self.running_event.clear()
            self.statusLabel.config(text="Disconnected due to inactivity")
            self.channelLabel.config(text="No channel")
            self.connectButton.config(text="Connect")
            
            try:
                self.clientSocket.close()
            except:
                pass
            
            self.clientSocket = None
            self.addMessage("You were disconnected due to inactivity. Use Connect to reconnect.", "red")
            
    def on_closing(self): # Handle window closing
        if self.clientSocket and self.running_event.is_set():
            self.disconnect() # Disconnect before closing
        self.root.destroy() # Close the window

    def toggleConnection(self): # Toggle connection state
        if self.clientSocket and self.running_event.is_set():
            # Currently connected, so disconnect
            self.disconnect()
        else:
            # Not connected, so show connect dialog
            self.showConnectDialog()

# Make this file runnable either as a module or standalone script
if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.mainloop()