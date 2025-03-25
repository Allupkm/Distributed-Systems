import tkinter as tk
from tkinter import ttk, scrolledtext

class MessageDisplay(scrolledtext.ScrolledText):
    """Enhanced message display with formatting support"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, wrap=tk.WORD, state=tk.DISABLED, **kwargs)
        
        # Configure text tags
        self.tag_configure("own_message", foreground="blue")
        self.tag_configure("system_message", foreground="gray", font=("Arial", 9, "italic"))
        self.tag_configure("error_message", foreground="red")
        self.tag_configure("dm_message", foreground="purple")
    
    def add_message(self, message, tag=None):
        """Add a message with optional formatting"""
        self.config(state=tk.NORMAL)
        self.insert(tk.END, message + "\n", tag)
        self.see(tk.END)  # Auto-scroll to bottom
        self.config(state=tk.DISABLED)

class ChannelList(ttk.Frame):
    """Channel list with join button and functionality"""
    def __init__(self, parent, join_command):
        super().__init__(parent)
        self.join_command = join_command
        
        # Channel list
        self.listbox = tk.Listbox(self)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        
        # Add new channel controls
        join_frame = ttk.Frame(self)
        join_frame.pack(fill=tk.X, expand=False, pady=5)
        
        self.entry = ttk.Entry(join_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        join_button = ttk.Button(join_frame, text="Join", 
                               command=self._join_channel)
        join_button.pack(side=tk.RIGHT, padx=5)
    
    def _join_channel(self):
        channel = self.entry.get().strip()
        if channel:
            self.join_command(channel)
            self.entry.delete(0, tk.END)
    
    def update_list(self, channels, current_channel):
        """Update the channel list and highlight current channel"""
        self.listbox.delete(0, tk.END)
        
        # Fix for empty lists or formatting issues
        if not channels or channels.isspace():
            return
            
        # Better splitting and handling of the channel list
        channels_list = [c.strip() for c in channels.split(",") if c.strip()]
        
        for channel in channels_list:
            self.listbox.insert(tk.END, channel)
        
        # Highlight current channel
        for i, channel in enumerate(channels_list):
            if channel.lower() == current_channel.lower():  # Case-insensitive comparison
                self.listbox.selection_set(i)
                break

class UserList(ttk.Frame):
    """User list with DM functionality"""
    def __init__(self, parent, dm_command):
        super().__init__(parent)
        self.dm_command = dm_command
        
        # User list
        self.listbox = tk.Listbox(self)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        
        # DM button
        dm_button = ttk.Button(self, text="Send DM", command=self._send_dm)
        dm_button.pack(pady=5)
    
    def _send_dm(self):
        selected = self.listbox.curselection()
        if selected:
            user = self.listbox.get(selected[0])
            self.dm_command(user)
    
    def update_list(self, users):
        """Update the user list"""
        self.listbox.delete(0, tk.END)
        
        # Fix for empty lists or formatting issues
        if not users or users.isspace():
            return
        
        # Better splitting and handling of the user list
        users_list = [u.strip() for u in users.split(",") if u.strip()]
        
        for user in users_list:
            self.listbox.insert(tk.END, user)