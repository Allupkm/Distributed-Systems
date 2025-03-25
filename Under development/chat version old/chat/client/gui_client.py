import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import local modules
from client.client_core import ChatClient
from client.gui_components import MessageDisplay, ChannelList, UserList

class ChatClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Client")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Create client instance
        self.client = ChatClient(
            message_callback=self.handle_message,
            status_callback=self.handle_status
        )
        
        # Server connection settings
        self.host = "127.0.0.1"
        self.port = 3000
        
        # Create the GUI
        self.create_widgets()
        
        # Start with the connection dialog
        self.root.after(100, self.connect_dialog)
    
    def create_widgets(self):
        # Main layout - split into left sidebar and right content
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left sidebar for channels and users
        self.sidebar_frame = ttk.Frame(self.paned_window, width=200)
        self.paned_window.add(self.sidebar_frame, weight=1)
        
        # Channel and user lists in sidebar
        sidebar_notebook = ttk.Notebook(self.sidebar_frame)
        sidebar_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Channels tab
        self.channels_tab = ChannelList(sidebar_notebook, self.join_channel)
        sidebar_notebook.add(self.channels_tab, text="Channels")
        
        # Users tab
        self.users_tab = UserList(sidebar_notebook, self.prompt_dm)
        sidebar_notebook.add(self.users_tab, text="Users")
        
        # Right content area
        content_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(content_frame, weight=3)
        
        # Message display area
        self.message_display = MessageDisplay(content_frame)
        self.message_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Message composition area
        message_frame = ttk.Frame(content_frame)
        message_frame.pack(fill=tk.X, expand=False, padx=10, pady=5)
        
        self.message_entry = ttk.Entry(message_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind("<Return>", lambda event: self.send_message())
        
        send_button = ttk.Button(message_frame, text="Send", command=self.send_message)
        send_button.pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Disconnected")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=2)
        
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Connect", command=self.connect_dialog)
        file_menu.add_command(label="Disconnect", command=self.disconnect)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit_app)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def connect_dialog(self):
        """Show dialog to connect to server"""
        # Get server address
        self.host = simpledialog.askstring("Connect", "Enter server address:", 
                                         initialvalue=self.host)
        if not self.host:
            self.host = "127.0.0.1"
        
        # Get server port
        port_str = simpledialog.askstring("Connect", "Enter server port:", 
                                       initialvalue=str(self.port))
        if port_str and port_str.isdigit():
            self.port = int(port_str)
        
        # Get nickname
        nickname = None
        while not nickname:
            nickname = simpledialog.askstring("Connect", "Enter your nickname:")
            if not nickname:
                if not messagebox.askyesno("Retry", "Nickname cannot be empty. Try again?"):
                    return
        
        # Connect to server
        self.message_display.add_message(f"Connecting to {self.host}:{self.port}...", "system_message")
        self.client.connect(self.host, self.port, nickname)
    
    def handle_message(self, msg_type, content):
        """Handle messages from the client core"""
        # Add debug info for list messages
        if msg_type == "clients":
            print(f"DEBUG - Received clients list: '{content}'")
            self.users_tab.update_list(content)
            self.message_display.add_message(f"Online clients: {content}", "system_message")
        elif msg_type == "channels":
            print(f"DEBUG - Received channels list: '{content}'")
            self.channels_tab.update_list(content, self.client.current_channel)
            self.message_display.add_message(f"Available channels: {content}", "system_message")
        elif msg_type == "message":
            self.message_display.add_message(content)
        elif msg_type == "message_sent":
            self.message_display.add_message(f"You: {content}", "own_message")
        elif msg_type == "dm_received":
            sender, text = content
            self.message_display.add_message(f"DM from {sender}: {text}", "dm_message")
        elif msg_type == "dm_sent":
            receiver, text = content
            self.message_display.add_message(f"DM to {receiver}: {text}", "own_message")
        elif msg_type == "system":
            self.message_display.add_message(content, "system_message")
        elif msg_type == "error":
            self.message_display.add_message(content, "error_message")
        elif msg_type == "other":
            self.message_display.add_message(content)
    
    def handle_status(self, status_type, message):
        """Handle status updates from the client core"""
        if status_type == "connected":
            self.status_var.set(message)
            self.message_display.add_message(message, "system_message")
        elif status_type == "disconnected":
            self.status_var.set("Disconnected")
            if message:
                self.message_display.add_message(message, "system_message")
        elif status_type == "error":
            self.message_display.add_message(message, "error_message")
    
    def send_message(self):
        """Send the message in the entry field"""
        if not self.client.running_event.is_set():
            messagebox.showerror("Error", "Not connected to server")
            return
            
        message = self.message_entry.get().strip()
        if not message:
            return
            
        # Clear the entry field
        self.message_entry.delete(0, tk.END)
        
        # Process commands or send as regular message
        if message.startswith("/"):
            self.process_command(message[1:])
        else:
            self.client.send_message(message)
    
    def process_command(self, command):
        """Process chat commands like /join, /dm etc."""
        parts = command.split(" ", 1)
        cmd = parts[0].upper()
        
        if cmd == "JOIN" and len(parts) > 1:
            self.join_channel(parts[1])
        elif cmd == "DM" and len(parts) > 1:
            dm_parts = parts[1].split(" ", 1)
            if len(dm_parts) == 2:
                self.client.send_dm(dm_parts[0], dm_parts[1])
            else:
                self.message_display.add_message("Invalid DM format. Use: /dm <client> <message>", "error_message")
        elif cmd == "LIST" and len(parts) > 1:
            if parts[1].upper() == "CHANNELS":
                self.client.list_channels()
            elif parts[1].upper() == "CLIENTS":
                self.client.list_clients()
            else:
                self.message_display.add_message("Invalid list command. Use: /list channels or /list clients", "error_message")
        elif cmd == "QUIT":
            self.disconnect()
        elif cmd == "HELP":
            self.show_help()
        else:
            self.message_display.add_message(f"Unknown command: {cmd}. Type /help for available commands.", "error_message")
    
    def join_channel(self, channel):
        """Join a channel"""
        if not channel:
            messagebox.showwarning("Warning", "Channel name cannot be empty")
            return
            
        self.client.join_channel(channel)
    
    def prompt_dm(self, recipient):
        """Show dialog to send DM"""
        message = simpledialog.askstring("Direct Message", f"Enter message for {recipient}:")
        if message:
            self.client.send_dm(recipient, message)
    
    def disconnect(self):
        """Disconnect from server"""
        self.client.disconnect()
    
    def show_help(self):
        """Show help information"""
        help_text = """
Available Commands:
/join <channel> - Join a channel
/dm <user> <message> - Send a direct message
/list channels - List available channels
/list clients - List online clients
/quit - Disconnect from server
/help - Show this help message

You can also use the GUI buttons and menus for most actions.
"""
        self.message_display.add_message(help_text, "system_message")
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", "Chat Client\n\nA GUI chat client for the distributed systems assignment.")
    
    def quit_app(self):
        """Quit the application"""
        if self.client.running_event.is_set():
            if messagebox.askyesno("Confirm", "Disconnect from server and quit?"):
                self.disconnect()
                self.root.quit()
        else:
            self.root.quit()

def main():
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)  # Handle window close button
    root.mainloop()

if __name__ == "__main__":
    main()