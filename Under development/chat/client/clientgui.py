import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog, messagebox

class ChatClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Application")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)
        
        # Connection variables
        self.clientSocket = None
        self.running_event = threading.Event()
        self.nickname = None
        self.current_channel = "general"
        
        # Create GUI elements
        self.create_widgets()
        
        # Start connection dialog
        self.connect_dialog()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create horizontal panes (sidebar and main content)
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar for channels and users
        sidebar_frame = ttk.Frame(paned_window, width=200)
        
        # Channels section
        channels_frame = ttk.LabelFrame(sidebar_frame, text="Channels")
        channels_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.channels_tree = ttk.Treeview(channels_frame, height=10)
        self.channels_tree.heading("#0", text="Available Channels")
        self.channels_tree.pack(fill=tk.BOTH, expand=True)
        self.channels_tree.bind("<Double-1>", self.on_channel_select)
        
        # Users section
        users_frame = ttk.LabelFrame(sidebar_frame, text="Online Users")
        users_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.users_tree = ttk.Treeview(users_frame, height=15)
        self.users_tree.heading("#0", text="Users")
        self.users_tree.pack(fill=tk.BOTH, expand=True)
        self.users_tree.bind("<Double-1>", self.on_user_select)
        
        # Main chat area
        chat_frame = ttk.Frame(paned_window)
        
        # Chat header showing current channel
        self.channel_label = ttk.Label(chat_frame, text="Channel: general", font=("TkDefaultFont", 12, "bold"))
        self.channel_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state='disabled')
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Message input area
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        self.message_input = ttk.Entry(input_frame)
        self.message_input.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.message_input.bind("<Return>", self.send_message)
        
        send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        send_button.pack(side=tk.RIGHT, padx=5)
        
        # Add frames to paned window
        paned_window.add(sidebar_frame, weight=1)
        paned_window.add(chat_frame, weight=3)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # Create menu
        self.create_menu()
        
    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Connect", command=self.connect_dialog)
        file_menu.add_command(label="Disconnect", command=self.disconnect)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        
        # Channel menu
        channel_menu = tk.Menu(menu_bar, tearoff=0)
        channel_menu.add_command(label="Join Channel", command=self.join_channel_dialog)
        channel_menu.add_command(label="Refresh Channel List", command=lambda: self.list_channels_users("CHANNELS"))
        menu_bar.add_cascade(label="Channel", menu=channel_menu)
        
        # Users menu
        users_menu = tk.Menu(menu_bar, tearoff=0)
        users_menu.add_command(label="Refresh User List", command=lambda: self.list_channels_users("CLIENTS"))
        menu_bar.add_cascade(label="Users", menu=users_menu)
        
        self.root.config(menu=menu_bar)
    
    def connect_dialog(self):
        # Create a dialog for connection details
        dialog = tk.Toplevel(self.root)
        dialog.title("Connect to Server")
        dialog.geometry("350x250")  # Made slightly taller to ensure button visibility
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create a frame for the form contents
        form_frame = ttk.Frame(dialog, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Server address
        ttk.Label(form_frame, text="Server Address:").pack(anchor="w", pady=(0, 2))
        host_var = tk.StringVar(value="127.0.0.1")
        host_entry = ttk.Entry(form_frame, textvariable=host_var)
        host_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Port
        ttk.Label(form_frame, text="Server Port:").pack(anchor="w", pady=(0, 2))
        port_var = tk.StringVar(value="3000")
        port_entry = ttk.Entry(form_frame, textvariable=port_var)
        port_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Nickname
        ttk.Label(form_frame, text="Nickname:").pack(anchor="w", pady=(0, 2))
        nickname_var = tk.StringVar()
        nickname_entry = ttk.Entry(form_frame, textvariable=nickname_var)
        nickname_entry.pack(fill=tk.X, pady=(0, 10))
        nickname_entry.focus_set()  # Set focus on nickname field
        
        # Define the connect function before using it
        def connect():
            host = host_var.get()
            try:
                port = int(port_var.get())
                if port < 1 or port > 65535:
                    messagebox.showerror("Error", "Port must be between 1 and 65535")
                    return
            except ValueError:
                messagebox.showerror("Error", "Port must be a number")
                return
                
            nickname = nickname_var.get()
            
            if not nickname:
                messagebox.showerror("Error", "Please enter a nickname")
                return
                
            dialog.destroy()
            self.connect_to_server(host, port, nickname)
        
        # Button frame for connect button
        button_frame = ttk.Frame(dialog)
        connect_button = ttk.Button(button_frame, text="Connect", command=connect)
        connect_button.pack(pady=5, padx=10, ipadx=10)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Bind Enter key to connect function
        dialog.bind("<Return>", lambda event: connect())
        
        # Make sure dialog appears on top and takes focus
        dialog.focus_set()
    
    def connect_to_server(self, host, port, nickname, admin_creds=None):
        try:
            self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.clientSocket.connect((host, port))
            
            # Set nickname
            self.clientSocket.send(f"NICKNAME:{nickname}".encode("utf-8"))
            response = self.clientSocket.recv(1024).decode("utf-8")
            
            if response.startswith("ERROR:"):
                messagebox.showerror("Error", response[6:])
                self.clientSocket.close()
                return
            
            self.nickname = nickname
            self.running_event.set()
            
            # Start message receiving thread
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            self.status_var.set(f"Connected as {nickname}")
            self.add_message_to_chat("System", "Connected to server")
            
            # Request initial channel and user lists
            self.list_channels_users("CHANNELS")
            self.list_channels_users("CLIENTS")
            
            # If admin credentials were provided, try to authenticate
            if admin_creds:
                admin_user, admin_pass = admin_creds
                self.clientSocket.send(f"ADMIN_AUTH:{admin_user}:{admin_pass}".encode("utf-8"))
                # The server will respond with INFO or ERROR message
            
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
    
    def receive_messages(self):
        try:
            while self.running_event.is_set():
                try:
                    message = self.clientSocket.recv(1024).decode("utf-8")
                    
                    if not message:
                        self.add_message_to_chat("System", "Connection to server lost")
                        self.running_event.clear()
                        break
                    
                    if message.startswith("MSG:"):
                        # Extract timestamp and message
                        parts = message[4:].split(":", 1)
                        if len(parts) == 2:
                            timestamp, content = parts
                            self.add_message_to_chat("Chat", content, timestamp=timestamp)
                        else:
                            self.add_message_to_chat("Chat", message[4:])
                    elif message.startswith("MSG_SENT:"):
                        # No action needed - message already shown in input
                        pass
                    elif message.startswith("PRIVATE:"):
                        parts = message.split(":", 3)
                        if len(parts) >= 4:
                            timestamp = parts[1]
                            sender = parts[2]
                            content = parts[3]
                            self.add_message_to_chat(f"DM from {sender}", content, tag="dm", timestamp=timestamp)
                    elif message.startswith("PRIVATE_SENT:"):
                        parts = message.split(":", 3)
                        if len(parts) >= 4:
                            timestamp = parts[1]
                            receiver = parts[2]
                            content = parts[3]
                            self.add_message_to_chat(f"DM to {receiver}", content, tag="dm", timestamp=timestamp)
                    elif message.startswith("CLIENTS:"):
                        clients_list = message[8:]
                        self.update_users_list(clients_list)
                    elif message.startswith("CHANNELS:"):
                        channels_list = message[9:]
                        self.update_channels_list(channels_list)
                    # When receiving INFO messages that indicate history
                    elif message.startswith("INFO:"):
                        parts = message.split(":", 2)
                        if len(parts) >= 3:
                            timestamp = parts[1]
                            info_message = parts[2]
                            
                            # Add visual separator for history
                            if "Begin History" in info_message:
                                self.chat_display.config(state='normal')
                                self.chat_display.insert(tk.END, "\n" + "="*50 + "\n", "separator")
                                self.chat_display.insert(tk.END, f"[{timestamp}] {info_message}\n", "system")
                                self.chat_display.config(state='disabled')
                            elif "End History" in info_message:
                                self.chat_display.config(state='normal')
                                self.chat_display.insert(tk.END, f"[{timestamp}] {info_message}\n", "system")
                                self.chat_display.insert(tk.END, "="*50 + "\n\n", "separator")
                                self.chat_display.config(state='disabled')
                            else:
                                self.add_message_to_chat("Info", info_message, timestamp=timestamp)
                        else:
                            self.add_message_to_chat("Info", message[5:])
                    elif message.startswith("ERROR:"):
                        self.add_message_to_chat("Error", message[6:])
                    elif message.startswith("QUIT"):
                        self.add_message_to_chat("System", "Server disconnected")
                        self.running_event.clear()
                        break
                    elif message.startswith("KICKED:"):
                        self.add_message_to_chat("System", f"You were kicked: {message[7:]}")
                        self.running_event.clear()
                        break
                    elif message.startswith("HISTORY:"):
                        parts = message.split(":", 3)
                        if len(parts) >= 4:
                            timestamp = parts[1]
                            sender = parts[2]
                            content = parts[3]
                            self.add_message_to_chat(f"{sender}", content, tag="history", timestamp=timestamp)
                    else:
                        self.add_message_to_chat("Server", message)
                        
                except socket.error:
                    self.add_message_to_chat("System", "Connection error")
                    self.running_event.clear()
                    break
                    
        except Exception as e:
            self.add_message_to_chat("System", f"Error receiving messages: {e}")
            self.running_event.clear()
    
    def add_message_to_chat(self, sender, content, tag=None, timestamp=None):
        self.chat_display.config(state='normal')
        
        # Format message with timestamp if available
        time_prefix = f"[{timestamp}] " if timestamp else ""
        
        # Format based on message type
        if sender == "System" or sender == "Error":
            self.chat_display.insert(tk.END, f"{time_prefix}[{sender}] {content}\n", "system")
        elif sender.startswith("DM"):
            self.chat_display.insert(tk.END, f"{time_prefix}[{sender}] {content}\n", "dm")
        elif tag == "history":
            self.chat_display.insert(tk.END, f"{time_prefix}[{sender}] {content}\n", "history")
        else:
            self.chat_display.insert(tk.END, f"{time_prefix}[{sender}] {content}\n")
            
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')
        
        # Configure tags for different message types
        self.chat_display.tag_configure("system", foreground="blue")
        self.chat_display.tag_configure("error", foreground="red")
        self.chat_display.tag_configure("dm", foreground="green")
        self.chat_display.tag_configure("history", foreground="#707070")  # Slightly grayed out
    
    def update_users_list(self, users_str):
        # Clear current list
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
            
        # Add users to list
        for user in users_str.split(", "):
            if user.strip():
                self.users_tree.insert("", "end", text=user.strip())
    
    def update_channels_list(self, channels_str):
        # Clear current list
        for item in self.channels_tree.get_children():
            self.channels_tree.delete(item)
            
        # Add channels to list
        for channel in channels_str.split(", "):
            if channel.strip():
                self.channels_tree.insert("", "end", text=channel.strip())
    
    def send_message(self, event=None):
        message = self.message_input.get().strip()
        if not message:
            return
            
        self.message_input.delete(0, tk.END)
        
        if message.startswith("/"):
            self.handle_command(message)
        else:
            try:
                self.clientSocket.send(f"MSG:{message}".encode("utf-8"))
                self.add_message_to_chat(self.nickname, message)
            except Exception as e:
                self.add_message_to_chat("Error", f"Failed to send message: {e}")
    
    def handle_command(self, command):
        parts = command[1:].split(" ", 1)
        cmd = parts[0].upper()
        
        if cmd == "JOIN" and len(parts) > 1:
            channel = parts[1]
            self.join_channel(channel)
        elif cmd == "DM" and len(parts) > 1:
            dm_parts = parts[1].split(" ", 1)
            if len(dm_parts) == 2:
                self.send_direct_message(dm_parts[0], dm_parts[1])
            else:
                self.add_message_to_chat("Error", "Invalid DM format. Use: /dm <client> <message>")
        elif cmd == "LIST":
            if len(parts) > 1:
                if parts[1].upper() == "CHANNELS":
                    self.list_channels_users("CHANNELS")
                elif parts[1].upper() == "CLIENTS":
                    self.list_channels_users("CLIENTS")
                else:
                    self.add_message_to_chat("Error", "Invalid list command. Use: /list channels or /list clients")
        elif cmd == "QUIT":
            self.disconnect()
        elif cmd == "HELP":
            self.show_help()
        else:
            self.add_message_to_chat("Error", "Invalid command")
    
    def join_channel(self, channel):
        try:
            self.clientSocket.send(f"JOIN:{channel}".encode("utf-8"))
            
            # Clear the chat display when joining a new channel
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            # Add a header message for the new channel
            self.add_message_to_chat("System", f"You joined channel: {channel}")
            
            # Update current channel in UI
            self.current_channel = channel
            self.channel_label.config(text=f"Channel: {channel}")
            
        except Exception as e:
            self.add_message_to_chat("Error", f"Failed to join channel: {e}")
    
    def join_channel_dialog(self):
        channel = simpledialog.askstring("Join Channel", "Enter channel name:")
        if channel:
            self.join_channel(channel)
    
    def send_direct_message(self, recipient, message):
        try:
            self.clientSocket.send(f"DM:{recipient}:{message}".encode("utf-8"))
        except Exception as e:
            self.add_message_to_chat("Error", f"Failed to send DM: {e}")
    
    def list_channels_users(self, list_type):
        try:
            self.clientSocket.send(f"LIST:{list_type}".encode("utf-8"))
        except Exception as e:
            self.add_message_to_chat("Error", f"Failed to get list: {e}")
    
    def disconnect(self):
        if not self.running_event.is_set():
            return
            
        try:
            self.clientSocket.send("QUIT".encode("utf-8"))
        except:
            pass
            
        self.running_event.clear()
        
        try:
            self.clientSocket.close()
        except:
            pass
            
        self.status_var.set("Disconnected")
        self.add_message_to_chat("System", "Disconnected from server")
    
    def show_help(self):
        help_text = """
Available commands:
/join <channel> - Join a channel
/dm <client> <message> - Send a direct message
/list channels - List available channels
/list clients - List online users
/quit - Disconnect from server

You can also:
- Double-click on a channel to join it
- Double-click on a user to start a DM
"""
        self.add_message_to_chat("Help", help_text)
    
    def on_channel_select(self, event):
        item = self.channels_tree.selection()[0]
        channel = self.channels_tree.item(item, "text")
        self.join_channel(channel)
    
    def on_user_select(self, event):
        item = self.users_tree.selection()[0]
        user = self.users_tree.item(item, "text")
        
        # Ask for message
        message = simpledialog.askstring("Direct Message", f"Message to {user}:")
        if message:
            self.send_direct_message(user, message)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.mainloop()