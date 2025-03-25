import sys
import tkinter as tk
import os
import subprocess
import time
from tkinter import simpledialog, messagebox

def start_server():
    """Start the chat server in a new process"""
    subprocess.Popen([sys.executable, "chat/server/server.py"], 
                     creationflags=subprocess.CREATE_NEW_CONSOLE)

def start_client():
    """Start the GUI client"""
    from chat.client.gui_client import main
    main()

def start_registry():
    """Start the registry server in a new process"""
    try:
        # Make sure the path exists
        registry_path = os.path.join("chat", "registry", "registry_server.py")
        if not os.path.exists(registry_path):
            print(f"ERROR: Registry server file not found at {registry_path}")
            messagebox.showerror("Error", f"Registry server file not found at {registry_path}")
            return
            
        print(f"Starting registry server from {registry_path}...")
        # Add environment variable to keep console open
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output
        process = subprocess.Popen([sys.executable, registry_path], 
                                  creationflags=subprocess.CREATE_NEW_CONSOLE,
                                  env=env)
        
        # Check if process is still running after a short delay
        time.sleep(1)
        if process.poll() is not None:
            print("Registry server failed to start")
            messagebox.showerror("Error", "Registry server failed to start")
        else:
            print("Registry server process started")
            messagebox.showinfo("Success", "Registry server started successfully")
    except Exception as e:
        print(f"Failed to start registry server: {e}")
        messagebox.showerror("Error", f"Failed to start registry server: {e}")

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Application Launcher")
        self.root.geometry("300x250")  # Make a bit taller
        
        frame = tk.Frame(root, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Chat Application", font=("Arial", 16)).pack(pady=10)
        
        # Add button for registry server
        tk.Button(frame, text="Start Registry Server", 
                 command=start_registry, 
                 width=20, height=2).pack(pady=5)
        
        tk.Button(frame, text="Start Chat Server", 
                 command=self.start_server, 
                 width=20, height=2).pack(pady=5)
        
        tk.Button(frame, text="Start Client", 
                 command=self.start_client, 
                 width=20, height=2).pack(pady=5)
        
        tk.Button(frame, text="Exit", 
                 command=root.quit, 
                 width=20).pack(pady=10)
    
    def start_client(self):
        """Start client and close launcher"""
        self.root.destroy()
        start_client()

    def start_server(self):
        """Configure and start server"""
        server_name = simpledialog.askstring("Server Name", "Enter server name:", 
                                           initialvalue="Chat Server")
        if server_name:
            # Pass server name as environment variable
            env = os.environ.copy()
            env["SERVER_NAME"] = server_name
            subprocess.Popen([sys.executable, "chat/server/server.py"], 
                             env=env,
                             creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == "__main__":
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()