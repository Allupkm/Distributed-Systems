import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog, messagebox
import threading
import socket
import time
import sys
import os
from datetime import datetime

# Import server functionality
import server

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Server Admin Panel")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Server state
        self.server_running = False
        self.server_thread = None
        self.server_socket = None
        
        # Stats variables
        self.stats = {
            "start_time": None,
            "connections": 0,
            "messages": 0,
            "active_clients": 0
        }
        
        # Initialize admin credentials BEFORE creating widgets
        self.admin_credentials = {}  # Dictionary to store username:password pairs
        self.current_admin = None
        
        # Create flag to indicate if UI is ready
        self.ui_initialized = False
        
        # Load credentials silently (without logging)
        self.load_admin_credentials_silent()
        
        # Now create the UI
        self.create_widgets()
        
        # Mark UI as ready
        self.ui_initialized = True
        
        # Log that we loaded credentials (now that UI exists)
        if self.admin_credentials:
            self.log_message("info", f"Loaded {len(self.admin_credentials)} admin accounts")
        
        # Setup auto-refresh
        self.setup_auto_refresh()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Dashboard
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="Dashboard")
        self.setup_dashboard(dashboard_frame)
        
        # Tab 2: Clients
        clients_frame = ttk.Frame(notebook)
        notebook.add(clients_frame, text="Clients")
        self.setup_clients_tab(clients_frame)
        
        # Tab 3: Channels
        channels_frame = ttk.Frame(notebook)
        notebook.add(channels_frame, text="Channels")
        self.setup_channels_tab(channels_frame)
        
        # Tab 4: Logs
        logs_frame = ttk.Frame(notebook)
        notebook.add(logs_frame, text="Logs")
        self.setup_logs_tab(logs_frame)
        
        # Tab 5: Settings
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        self.setup_settings_tab(settings_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Server not running")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
    
    def setup_dashboard(self, parent):
        # Dashboard layout with two columns
        left_frame = ttk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        right_frame = ttk.Frame(parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Server control panel
        control_frame = ttk.LabelFrame(left_frame, text="Server Control")
        control_frame.pack(fill=tk.X, pady=10, padx=5)
        
        control_buttons = ttk.Frame(control_frame)
        control_buttons.pack(fill=tk.X, pady=10, padx=10)
        
        self.start_button = ttk.Button(control_buttons, text="Start Server", command=self.start_server)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_buttons, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_buttons, text="Refresh", command=self.refresh_all).pack(side=tk.RIGHT, padx=5)
        
        # Server info panel
        info_frame = ttk.LabelFrame(left_frame, text="Server Information")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        # Host and port
        host_frame = ttk.Frame(info_frame)
        host_frame.pack(fill=tk.X, pady=(10, 5), padx=10)
        
        ttk.Label(host_frame, text="Host:").pack(side=tk.LEFT)
        self.host_var = tk.StringVar(value=server.HOST)
        ttk.Entry(host_frame, textvariable=self.host_var).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)
        
        port_frame = ttk.Frame(info_frame)
        port_frame.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Label(port_frame, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value=str(server.PORT))
        ttk.Entry(port_frame, textvariable=self.port_var).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)
        
        # Connection info display
        connection_info_frame = ttk.LabelFrame(info_frame, text="Connection Information")
        connection_info_frame.pack(fill=tk.X, pady=10, padx=10)

        # Local network IP
        network_frame = ttk.Frame(connection_info_frame)
        network_frame.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(network_frame, text="Network IP:").pack(side=tk.LEFT)
        self.network_ip_var = tk.StringVar(value=server.get_local_ip())
        network_entry = ttk.Entry(network_frame, textvariable=self.network_ip_var, state="readonly")
        network_entry.pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        # Local IP
        local_frame = ttk.Frame(connection_info_frame)
        local_frame.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(local_frame, text="Local IP:").pack(side=tk.LEFT)
        self.local_ip_var = tk.StringVar(value="127.0.0.1")
        local_entry = ttk.Entry(local_frame, textvariable=self.local_ip_var, state="readonly")
        local_entry.pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        # Copy buttons
        ttk.Button(connection_info_frame, text="Copy Network Address", 
                   command=lambda: self.root.clipboard_append(f"{self.network_ip_var.get()}:{server.PORT}")
                  ).pack(fill=tk.X, pady=(5, 0), padx=5)
        ttk.Button(connection_info_frame, text="Copy Local Address", 
                   command=lambda: self.root.clipboard_append(f"127.0.0.1:{server.PORT}")
                  ).pack(fill=tk.X, pady=5, padx=5)
        
        # Stats section
        stats_frame = ttk.LabelFrame(right_frame, text="Server Statistics")
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        # Uptime
        uptime_frame = ttk.Frame(stats_frame)
        uptime_frame.pack(fill=tk.X, pady=5, padx=10)
        ttk.Label(uptime_frame, text="Uptime:").pack(side=tk.LEFT)
        self.uptime_var = tk.StringVar(value="Not running")
        ttk.Label(uptime_frame, textvariable=self.uptime_var).pack(side=tk.LEFT, padx=(5, 0))
        
        # Active clients
        clients_frame = ttk.Frame(stats_frame)
        clients_frame.pack(fill=tk.X, pady=5, padx=10)
        ttk.Label(clients_frame, text="Active Clients:").pack(side=tk.LEFT)
        self.active_clients_var = tk.StringVar(value="0")
        ttk.Label(clients_frame, textvariable=self.active_clients_var).pack(side=tk.LEFT, padx=(5, 0))
        
        # Active channels
        channels_frame = ttk.Frame(stats_frame)
        channels_frame.pack(fill=tk.X, pady=5, padx=10)
        ttk.Label(channels_frame, text="Active Channels:").pack(side=tk.LEFT)
        self.active_channels_var = tk.StringVar(value="0")
        ttk.Label(channels_frame, textvariable=self.active_channels_var).pack(side=tk.LEFT, padx=(5, 0))
        
        # Total connections
        connections_frame = ttk.Frame(stats_frame)
        connections_frame.pack(fill=tk.X, pady=5, padx=10)
        ttk.Label(connections_frame, text="Total Connections:").pack(side=tk.LEFT)
        self.connections_var = tk.StringVar(value="0")
        ttk.Label(connections_frame, textvariable=self.connections_var).pack(side=tk.LEFT, padx=(5, 0))
        
        # Recent activity panel
        activity_frame = ttk.LabelFrame(right_frame, text="Recent Activity")
        activity_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        self.activity_text = scrolledtext.ScrolledText(activity_frame, height=10)
        self.activity_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.activity_text.config(state=tk.DISABLED)
    
    def setup_clients_tab(self, parent):
        # Clients management area
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(controls_frame, text="Client Management").pack(side=tk.LEFT)
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_clients).pack(side=tk.RIGHT, padx=5)
        
        # Treeview for clients
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        columns = ("Nickname", "IP Address", "Connected Since", "Last Activity", "Current Channel")
        self.clients_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        # Add headings
        for col in columns:
            self.clients_tree.heading(col, text=col)
            self.clients_tree.column(col, width=100)
        
        # Add scrollbars
        yscroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.clients_tree.yview)
        self.clients_tree.configure(yscrollcommand=yscroll.set)
        
        self.clients_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Button(action_frame, text="Kick Client", command=self.kick_selected_client).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Ban Client", command=self.ban_selected_client).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Message Client", command=self.message_selected_client).pack(side=tk.LEFT, padx=5)
        
    def setup_channels_tab(self, parent):
        # Channels management
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(controls_frame, text="Channel Management").pack(side=tk.LEFT)
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_channels).pack(side=tk.RIGHT, padx=5)
        ttk.Button(controls_frame, text="Create Channel", command=self.create_channel_dialog).pack(side=tk.RIGHT, padx=5)
        
        # Split view: left for channels list, right for channel users
        paned_window = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        # Left side: Channels
        channels_frame = ttk.Frame(paned_window)
        channels_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(channels_frame, text="Channels").pack(fill=tk.X)
        
        self.channels_tree = ttk.Treeview(channels_frame, columns=("Channel", "Users"), show="headings")
        self.channels_tree.heading("Channel", text="Channel")
        self.channels_tree.heading("Users", text="Users")
        self.channels_tree.column("Channel", width=150)
        self.channels_tree.column("Users", width=50)
        self.channels_tree.pack(fill=tk.BOTH, expand=True)
        self.channels_tree.bind("<<TreeviewSelect>>", self.on_channel_select)
        
        # Right side: Channel Users
        users_frame = ttk.Frame(paned_window)
        users_frame.pack(fill=tk.BOTH, expand=True)
        
        self.channel_users_label = ttk.Label(users_frame, text="Users in Channel")
        self.channel_users_label.pack(fill=tk.X)
        
        self.channel_users_tree = ttk.Treeview(users_frame, columns=("Nickname", "Connected Since"), show="headings")
        self.channel_users_tree.heading("Nickname", text="Nickname")
        self.channel_users_tree.heading("Connected Since", text="Connected Since")
        self.channel_users_tree.pack(fill=tk.BOTH, expand=True)
        
        # Add frames to paned window
        paned_window.add(channels_frame, weight=1)
        paned_window.add(users_frame, weight=2)
        
        # Action buttons 
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Button(action_frame, text="Send Channel Message", command=self.send_channel_message).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Delete Channel", command=self.delete_channel).pack(side=tk.LEFT, padx=5)
    
    def setup_logs_tab(self, parent):
        # Log filtering controls
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(controls_frame, text="Log Level:").pack(side=tk.LEFT)
        
        self.log_level_var = tk.StringVar(value="All")
        log_level_combo = ttk.Combobox(controls_frame, textvariable=self.log_level_var)
        log_level_combo['values'] = ('All', 'Info', 'Warning', 'Error', 'Debug')
        log_level_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.RIGHT, padx=5)
        ttk.Button(controls_frame, text="Export Logs", command=self.export_logs).pack(side=tk.RIGHT, padx=5)
        
        # Log display
        log_frame = ttk.Frame(parent)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        self.log_display = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.log_display.pack(fill=tk.BOTH, expand=True)
        self.log_display.config(state=tk.DISABLED)
        
        # Configure text tags
        self.log_display.tag_configure("info", foreground="blue")
        self.log_display.tag_configure("warning", foreground="orange")
        self.log_display.tag_configure("error", foreground="red")
        self.log_display.tag_configure("debug", foreground="gray")
    
    def setup_settings_tab(self, parent):
        # Server configuration settings
        settings_frame = ttk.LabelFrame(parent, text="Server Configuration")
        settings_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # Timeout settings
        timeout_frame = ttk.Frame(settings_frame)
        timeout_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(timeout_frame, text="Client Timeout (seconds):").pack(side=tk.LEFT)
        self.timeout_var = tk.StringVar(value=str(server.clientTimeout))
        ttk.Entry(timeout_frame, textvariable=self.timeout_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # Check interval
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(interval_frame, text="Check Interval (seconds):").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value=str(server.clientsCheckInterval))
        ttk.Entry(interval_frame, textvariable=self.interval_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # Max clients
        max_clients_frame = ttk.Frame(settings_frame)
        max_clients_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(max_clients_frame, text="Maximum Clients:").pack(side=tk.LEFT)
        self.max_clients_var = tk.StringVar(value="100")
        ttk.Entry(max_clients_frame, textvariable=self.max_clients_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # Save settings button
        ttk.Button(settings_frame, text="Apply Settings", command=self.save_settings).pack(pady=10)
        
        # Admin accounts section
        admin_frame = ttk.LabelFrame(parent, text="Admin Accounts")
        admin_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        admin_list_frame = ttk.Frame(admin_frame)
        admin_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.admin_list = ttk.Treeview(admin_list_frame, columns=("Username",), show="headings")
        self.admin_list.heading("Username", text="Admin Username")
        self.admin_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        admin_buttons = ttk.Frame(admin_frame)
        admin_buttons.pack(fill=tk.X, pady=5)
        
        ttk.Button(admin_buttons, text="Add Admin", command=self.add_admin).pack(side=tk.LEFT, padx=5)
        ttk.Button(admin_buttons, text="Remove Admin", command=self.remove_admin).pack(side=tk.LEFT, padx=5)
        
    def setup_auto_refresh(self):
        """Setup automatic refresh of UI elements"""
        def refresh_loop():
            while True:
                if self.server_running:
                    self.update_stats()
                    self.refresh_clients()
                    self.refresh_channels()
                time.sleep(5)  # Update every 5 seconds
        
        refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()
    
    def start_server(self):
        """Start the chat server"""
        try:
            # Update server variables from UI
            server.HOST = self.host_var.get()
            server.PORT = int(self.port_var.get())
            server.SERVERADDRESS = (server.HOST, server.PORT)
            
            # Apply settings
            self.save_settings()
            
            # Get local IP before starting server
            local_ip = server.get_local_ip()
            
            # Display connection information in the GUI
            self.log_message("info", f"Server starting on all interfaces (0.0.0.0:{server.PORT})")
            self.log_message("info", f"For clients to connect on your network, use: {local_ip}:{server.PORT}")
            self.log_message("info", f"For local connections, use: 127.0.0.1:{server.PORT}")
            
            # Add to activity feed as well for greater visibility
            self.add_activity(f"Server IP for network connections: {local_ip}:{server.PORT}")
            
            # Display in status bar for constant visibility
            self.status_var.set(f"Running on {local_ip}:{server.PORT}")
            
            # Start server in a new thread
            self.server_thread = threading.Thread(target=server.startServer)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.server_running = True
            self.stats["start_time"] = time.time()
            
            # Update UI
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            self.log_message("error", f"Failed to start server: {e}")
    
    def stop_server(self):
        """Stop the chat server"""
        try:
            # Notify all clients
            with server.acquirelocks():
                for client_data in server.clients.values():
                    try:
                        client_data['socket'].send("ERROR:Server is shutting down".encode("utf-8"))
                        client_data['socket'].close()
                    except:
                        pass
            
            # Reset server state
            self.server_running = False
            
            # Update UI
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_var.set("Server stopped")
            
            self.log_message("info", "Server stopped")
            self.add_activity("Server stopped")
            
            # Re-initialize server
            server.clients = {}
            server.channels = {"general": set()}
            
        except Exception as e:
            messagebox.showerror("Error", f"Error stopping server: {e}")
            self.log_message("error", f"Error stopping server: {e}")
    
    def refresh_all(self):
        """Refresh all dynamic data"""
        self.update_stats()
        self.refresh_clients()
        self.refresh_channels()
    
    def update_stats(self):
        """Update server statistics"""
        if self.server_running and self.stats["start_time"]:
            # Calculate uptime
            uptime_seconds = time.time() - self.stats["start_time"]
            hours, remainder = divmod(uptime_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            self.uptime_var.set(uptime_str)
            
            # Update client and channel counts
            self.active_clients_var.set(str(len(server.clients)))
            self.active_channels_var.set(str(len(server.channels)))
            
        else:
            self.uptime_var.set("Not running")
            self.active_clients_var.set("0")
            self.active_channels_var.set("0")
    
    def refresh_clients(self):
        """Update the clients treeview"""
        # Clear existing items
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)
            
        if not self.server_running:
            return
            
        # Add current clients
        current_time = time.time()
        with server.acquirelocks():
            for nickname, client_data in server.clients.items():
                connected_time = datetime.fromtimestamp(client_data['lastActivity'] - 10).strftime('%H:%M:%S')
                last_activity = datetime.fromtimestamp(client_data['lastActivity']).strftime('%H:%M:%S')
                
                # Get client's channel
                current_channel = "None"
                for channel, users in server.channels.items():
                    if nickname in users:
                        current_channel = channel
                        break
                
                # Get client's IP
                client_ip = "Unknown"
                try:
                    client_ip = client_data['socket'].getpeername()[0]
                except:
                    pass
                    
                self.clients_tree.insert("", "end", values=(
                    nickname, client_ip, connected_time, last_activity, current_channel
                ))
    
    def refresh_channels(self):
        """Update the channels treeview"""
        # Clear existing items
        for item in self.channels_tree.get_children():
            self.channels_tree.delete(item)
            
        if not self.server_running:
            return
            
        # Add current channels
        with server.channelsLock:
            for channel_name, users in server.channels.items():
                self.channels_tree.insert("", "end", values=(
                    channel_name, len(users)
                ))
    
    def on_channel_select(self, event):
        """When a channel is selected, show its users"""
        selection = self.channels_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        channel_name = self.channels_tree.item(item, "values")[0]
        
        # Update label
        self.channel_users_label.config(text=f"Users in channel: {channel_name}")
        
        # Clear existing items
        for item in self.channel_users_tree.get_children():
            self.channel_users_tree.delete(item)
            
        # Add channel users
        with server.channelsLock:
            if channel_name in server.channels:
                users = server.channels[channel_name]
                for nickname in users:
                    connected_time = "Unknown"
                    with server.clientsLock:
                        if nickname in server.clients:
                            connected_time = datetime.fromtimestamp(
                                server.clients[nickname]['lastActivity'] - 10
                            ).strftime('%H:%M:%S')
                            
                    self.channel_users_tree.insert("", "end", values=(
                        nickname, connected_time
                    ))
    
    def kick_selected_client(self):
        """Kick the selected client"""
        selection = self.clients_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a client to kick")
            return
            
        item = selection[0]
        nickname = self.clients_tree.item(item, "values")[0]
        
        reason = simpledialog.askstring("Kick Client", f"Reason for kicking {nickname}:", 
                                      initialvalue="Kicked by administrator")
        if reason is None:  # User cancelled
            return
            
        # Variables to track what happened during lock acquisition
        client_kicked = False
        
        # Implement kick function
        try:
            # Only hold locks for the data modification part
            with server.acquirelocks():
                # Find the user
                if nickname in server.clients:
                    # Get their channel
                    current_channel = None
                    for channel, users in server.channels.items():
                        if nickname in users:
                            current_channel = channel
                            break
                    
                    # Notify the user
                    try:
                        server.clients[nickname]['socket'].send(f"KICKED:{reason}".encode("utf-8"))
                        
                        # Notify channel if applicable
                        if current_channel:
                            server.broadcast(f"{nickname} has been kicked: {reason}", 
                                           current_channel, None, None, True)
                        
                        # Close connection
                        server.clients[nickname]['socket'].close()
                    except Exception as e:
                        print(f"Error during kick notification: {e}")  # Use print instead of log_message here
                    
                    # Remove from data structures
                    server.disconnectClient(nickname, True)
                    client_kicked = True
                
            # Now that locks are released, handle UI updates
            if client_kicked:
                # Update UI and logs
                messagebox.showinfo("Success", f"User {nickname} has been kicked")
                self.log_message("info", f"Kicked user: {nickname}, reason: {reason}")
                self.add_activity(f"Kicked user: {nickname}")
                
                # Refresh client list
                self.refresh_clients()
            else:
                messagebox.showinfo("Info", f"User {nickname} is no longer connected")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error kicking user: {e}")
            self.log_message("error", f"Error kicking user {nickname}: {e}")
    
    def ban_selected_client(self):
        """Ban the selected client"""
        # This would need to be implemented in the server module first
        messagebox.showinfo("Info", "Ban functionality not yet implemented")
    
    def message_selected_client(self):
        """Send a message to the selected client"""
        selection = self.clients_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a client to message")
            return
            
        item = selection[0]
        nickname = self.clients_tree.item(item, "values")[0]
        
        message = simpledialog.askstring("Send Message", f"Message to send to {nickname}:")
        if not message:
            return
            
        try:
            with server.clientsLock:
                if nickname in server.clients:
                    server.clients[nickname]['socket'].send(f"INFO:Server: {message}".encode("utf-8"))
                    messagebox.showinfo("Success", f"Message sent to {nickname}")
                    self.log_message("info", f"Sent message to {nickname}: {message}")
                else:
                    messagebox.showinfo("Info", f"User {nickname} is no longer connected")
        except Exception as e:
            messagebox.showerror("Error", f"Error sending message: {e}")
            self.log_message("error", f"Error messaging user {nickname}: {e}")
    
    def create_channel_dialog(self):
        """Open dialog to create a new channel"""
        channel_name = simpledialog.askstring("Create Channel", "Enter new channel name:")
        if not channel_name:
            return
            
        try:
            # Check if channel exists and create it if not
            channel_created = False
            with server.channelsLock:
                if channel_name in server.channels:
                    channel_exists = True
                else:
                    server.channels[channel_name] = set()
                    channel_created = True
        
            # Now that we've released the lock, show UI messages
            if not channel_created:
                messagebox.showinfo("Info", f"Channel {channel_name} already exists")
                return
                
            # Log and notify after releasing the lock
            messagebox.showinfo("Success", f"Channel {channel_name} created")
            self.log_message("info", f"Created channel: {channel_name}")
            self.add_activity(f"New channel created: {channel_name}")
            
            # Refresh channel list
            self.refresh_channels()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error creating channel: {e}")
            self.log_message("error", f"Error creating channel {channel_name}: {e}")
    
    def send_channel_message(self):
        """Send message to selected channel"""
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a channel")
            return
            
        item = selection[0]
        channel_name = self.channels_tree.item(item, "values")[0]
        
        message = simpledialog.askstring("Send to Channel", f"Message to send to {channel_name}:")
        if not message:
            return
            
        try:
            with server.acquirelocks():
                if channel_name in server.channels:
                    server.broadcast(f"SERVER: {message}", channel_name, None, None, True)
                    messagebox.showinfo("Success", f"Message sent to channel {channel_name}")
                    self.log_message("info", f"Sent message to channel {channel_name}: {message}")
                    self.add_activity(f"Message sent to {channel_name}")
                else:
                    messagebox.showinfo("Info", f"Channel {channel_name} no longer exists")
        except Exception as e:
            messagebox.showerror("Error", f"Error sending message: {e}")
            self.log_message("error", f"Error sending to channel {channel_name}: {e}")
    
    def delete_channel(self):
        """Delete selected channel"""
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a channel to delete")
            return
            
        item = selection[0]
        channel_name = self.channels_tree.item(item, "values")[0]
        
        if channel_name == "general":
            messagebox.showinfo("Info", "Cannot delete the general channel")
            return
            
        if not messagebox.askyesno("Confirm", f"Really delete channel {channel_name}?\nAll users will be moved to general."):
            return
            
        try:
            # Variables to track what happened during lock acquisition
            channel_deleted = False
            users_moved = []
            
            # Acquire locks only for the data modification part
            with server.acquirelocks():
                if channel_name in server.channels:
                    # Make sure general channel exists
                    if "general" not in server.channels:
                        server.channels["general"] = set()
                        
                    # Save users for notification after lock release
                    users_moved = list(server.channels[channel_name])
                    
                    # Move users to general channel
                    for user in users_moved:
                        server.channels["general"].add(user)
                    
                    # Delete the channel
                    del server.channels[channel_name]
                    channel_deleted = True
            
            # Now that locks are released, handle notifications and UI updates
            if channel_deleted:
                # Notify users they're being moved
                with server.clientsLock:  # Use smaller lock scope just for client access
                    for user in users_moved:
                        if user in server.clients:
                            try:
                                timestamp = datetime.now().strftime("%H:%M")
                                server.clients[user]['socket'].send(
                                    f"INFO:{timestamp}:Channel {channel_name} has been deleted. You have been moved to general.".encode("utf-8")
                                )
                            except:
                                pass
                
                # Update UI and logs
                messagebox.showinfo("Success", f"Channel {channel_name} deleted")
                self.log_message("info", f"Deleted channel: {channel_name}")
                self.add_activity(f"Channel deleted: {channel_name}")
                
                # Refresh channel list
                self.refresh_channels()
            else:
                messagebox.showinfo("Info", f"Channel {channel_name} no longer exists")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error deleting channel: {e}")
            self.log_message("error", f"Error deleting channel {channel_name}: {e}")
    
    def clear_logs(self):
        """Clear the log display"""
        self.log_display.config(state=tk.NORMAL)
        self.log_display.delete(1.0, tk.END)
        self.log_display.config(state=tk.DISABLED)
    
    def export_logs(self):
        """Export logs to a file"""
        try:
            filename = f"server_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, "w") as f:
                f.write(self.log_display.get(1.0, tk.END))
            messagebox.showinfo("Success", f"Logs exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Error exporting logs: {e}")
    
    def log_message(self, level, message):
        """Add a message to the log"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # If UI not initialized or log_display doesn't exist, print to console
        if not hasattr(self, 'ui_initialized') or not self.ui_initialized or not hasattr(self, 'log_display'):
            print(f"[{timestamp}] [{level.upper()}] {message}")
            return
        
        self.log_display.config(state=tk.NORMAL)
        
        # Only add if it matches the current filter level
        current_level = self.log_level_var.get().lower()
        if current_level == "all" or current_level == level:
            self.log_display.insert(tk.END, f"[{timestamp}] [{level.upper()}] {message}\n", level)
            self.log_display.see(tk.END)
            
        self.log_display.config(state=tk.DISABLED)
    
    def add_activity(self, message):
        """Add an activity message to the recent activity panel"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.activity_text.config(state=tk.NORMAL)
        self.activity_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.activity_text.see(tk.END)
        self.activity_text.config(state=tk.DISABLED)
    
    def save_settings(self):
        """Save server settings"""
        try:
            # Update server timeout settings
            server.clientTimeout = int(self.timeout_var.get())
            server.clientsCheckInterval = int(self.interval_var.get())
            
            messagebox.showinfo("Success", "Settings saved")
            self.log_message("info", "Server settings updated")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving settings: {e}")
            self.log_message("error", f"Error saving settings: {e}")
    
    def load_admin_credentials(self):
        """Load admin credentials from file"""
        try:
            admin_file = "admin_credentials.txt"
            if os.path.exists(admin_file):
                with open(admin_file, "r") as f:
                    for line in f:
                        if ":" in line:
                            username, password = line.strip().split(":", 1)
                            self.admin_credentials[username] = password
                self.log_message("info", f"Loaded {len(self.admin_credentials)} admin accounts")
        except Exception as e:
            self.log_message("error", f"Error loading admin credentials: {e}")

    def load_admin_credentials_silent(self):
        """Load admin credentials from file without logging"""
        try:
            admin_file = "admin_credentials.txt"
            if os.path.exists(admin_file):
                with open(admin_file, "r") as f:
                    for line in f:
                        if ":" in line:
                            username, password = line.strip().split(":", 1)
                            self.admin_credentials[username] = password
        except Exception as e:
            print(f"Error loading admin credentials: {e}")

    def save_admin_credentials(self):
        """Save admin credentials to file"""
        try:
            admin_file = "admin_credentials.txt"
            with open(admin_file, "w") as f:
                for username, password in self.admin_credentials.items():
                    f.write(f"{username}:{password}\n")
            return True
        except Exception as e:
            self.log_message("error", f"Error saving admin credentials: {e}")
            return False

    def add_admin(self):
        """Add a new admin account with password"""
        admin_name = simpledialog.askstring("New Admin", "Enter admin username:")
        if not admin_name:
            return
            
        # Check if username already exists
        if admin_name in self.admin_credentials:
            messagebox.showinfo("Info", "This admin username already exists")
            return
            
        # Ask for password
        admin_password = simpledialog.askstring("New Admin", 
                                              f"Enter password for {admin_name}:", 
                                              show='*')  # Show * for password characters
        if not admin_password:
            return
            
        # Confirm password
        confirm_password = simpledialog.askstring("New Admin", 
                                                "Confirm password:", 
                                                show='*')
        if admin_password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match")
            return
            
        # Store the credentials
        self.admin_credentials[admin_name] = admin_password
        
        # Add to the UI list (only show username, not password)
        self.admin_list.insert("", "end", values=(admin_name,))
        
        # Save credentials to file
        if self.save_admin_credentials():
            self.log_message("info", f"Added admin account: {admin_name}")
            messagebox.showinfo("Success", f"Admin account {admin_name} created successfully")
        else:
            messagebox.showwarning("Warning", "Admin account created but could not be saved to disk")

    def remove_admin(self):
        """Remove selected admin account"""
        selection = self.admin_list.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select an admin to remove")
            return
            
        item = selection[0]
        admin_name = self.admin_list.item(item, "values")[0]
        
        # Remove from credentials dictionary
        if admin_name in self.admin_credentials:
            del self.admin_credentials[admin_name]
            
        # Remove from UI
        self.admin_list.delete(selection[0])
        
        # Save updated credentials
        if self.save_admin_credentials():
            self.log_message("info", f"Removed admin account: {admin_name}")
        else:
            messagebox.showwarning("Warning", "Admin account removed but changes could not be saved to disk")

def login_dialog(root):
    """Show login dialog and authenticate admin user"""
    result = {"success": False}
    
    login_window = tk.Toplevel(root)
    login_window.title("Admin Login")
    login_window.geometry("300x150")
    login_window.transient(root)
    login_window.grab_set()  # Make window modal
    
    # Center the login window
    login_window.update_idletasks()
    width = login_window.winfo_width()
    height = login_window.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    login_window.geometry(f'+{x}+{y}')
    
    # Username field
    tk.Label(login_window, text="Username:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
    username_var = tk.StringVar()
    username_entry = ttk.Entry(login_window, textvariable=username_var)
    username_entry.grid(row=0, column=1, padx=10, pady=10)
    username_entry.focus_set()
    
    # Password field
    tk.Label(login_window, text="Password:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
    password_var = tk.StringVar()
    password_entry = ttk.Entry(login_window, textvariable=password_var, show="*")
    password_entry.grid(row=1, column=1, padx=10, pady=10)
    
    def authenticate():
        app = root.children["!servergui"]  # Get the ServerGUI instance
        if username_var.get() in app.admin_credentials and app.admin_credentials[username_var.get()] == password_var.get():
            app.current_admin = username_var.get()
            app.log_message("info", f"Admin user {username_var.get()} logged in")
            result["success"] = True
            login_window.destroy()
        else:
            messagebox.showerror("Error", "Invalid username or password")
    
    # Login button
    login_button = ttk.Button(login_window, text="Login", command=authenticate)
    login_button.grid(row=2, column=0, columnspan=2, pady=10)
    
    # Handle Enter key
    login_window.bind("<Return>", lambda event: authenticate())
    
    # Wait until this window is destroyed
    root.wait_window(login_window)
    return result["success"]

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    
    # Don't show the main window yet
    root.withdraw()
    
    # If there are admin accounts, require login
    if app.admin_credentials:
        if login_dialog(root):
            root.deiconify()  # Show main window after successful login
        else:
            root.destroy()  # Exit if login fails
    else:
        # First time use - no admin accounts yet
        if messagebox.askyesno("Setup", "No admin accounts found. Create one now?"):
            app.add_admin()
            # If at least one admin was created, show the main window
            if app.admin_credentials:
                root.deiconify()
            else:
                root.destroy()
        else:
            root.destroy()
    
    root.mainloop()