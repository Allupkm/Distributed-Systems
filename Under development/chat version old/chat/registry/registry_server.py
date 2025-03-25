import socket
import threading
import json
import time
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("registry.log"), logging.StreamHandler()]
)
logger = logging.getLogger("RegistryServer")

# Registry configuration
REGISTRY_PORT = 3999  # Fixed port for the registry service
SERVER_TIMEOUT = 300  # Seconds before a server entry expires without heartbeat

# Global server registry
# Format: {server_name: {"ip": ip, "port": port, "last_seen": timestamp}}
server_registry = {}
registry_lock = threading.Lock()

def start_registry_server():
    """Start the registry server to handle server registrations and lookups"""
    try:
        # Create UDP socket for the registry
        registry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        registry_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            registry_socket.bind(("0.0.0.0", REGISTRY_PORT))
            print(f"Registry server bound to port {REGISTRY_PORT}")
        except socket.error as e:
            logger.error(f"Failed to bind registry socket: {e}")
            print(f"ERROR: Could not bind to port {REGISTRY_PORT}. Is it already in use?")
            # Keep the console open for error viewing
            input("Press Enter to exit...")
            return
        
        logger.info(f"Registry server started on port {REGISTRY_PORT}")
        print(f"Registry server running on port {REGISTRY_PORT}...")
        
        # Start cleanup thread to remove expired servers
        cleanup_thread = threading.Thread(target=cleanup_expired_servers)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        # Main registry loop
        while True:
            try:
                print("Waiting for messages...")
                data, addr = registry_socket.recvfrom(1024)
                try:
                    message = json.loads(data.decode("utf-8"))
                    
                    if "action" not in message:
                        logger.warning(f"Received message without action from {addr}")
                        continue
                        
                    print(f"Received {message['action']} request from {addr}")
                    logger.info(f"Received {message['action']} request from {addr}")
                    
                    if message["action"] == "REGISTER":
                        handle_registration(message, addr, registry_socket)
                    elif message["action"] == "LOOKUP":
                        handle_lookup(message, addr, registry_socket)
                    elif message["action"] == "HEARTBEAT":
                        handle_heartbeat(message, addr, registry_socket)
                    elif message["action"] == "LIST":
                        handle_list_request(addr, registry_socket)
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON from {addr}")
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                print(f"Error processing message: {e}")
    except Exception as e:
        logger.error(f"Registry server failed: {e}")
        print(f"ERROR: Registry server failed: {e}")
        # Keep the console open for error viewing
        input("Press Enter to exit...")

def handle_registration(message, addr, socket):
    """Handle server registration request"""
    if "name" not in message or "port" not in message:
        response = {"status": "error", "message": "Missing required fields"}
        socket.sendto(json.dumps(response).encode("utf-8"), addr)
        return
        
    server_name = message["name"]
    server_port = message["port"]
    server_ip = addr[0]  # Use the sender's IP address
    
    with registry_lock:
        # Register or update server
        server_registry[server_name] = {
            "ip": server_ip,
            "port": server_port,
            "last_seen": time.time()
        }
    
    logger.info(f"Registered server '{server_name}' at {server_ip}:{server_port}")
    
    # Send confirmation
    response = {"status": "success", "message": f"Server '{server_name}' registered"}
    socket.sendto(json.dumps(response).encode("utf-8"), addr)

def handle_lookup(message, addr, socket):
    """Handle client lookup request"""
    if "name" not in message:
        response = {"status": "error", "message": "Missing server name"}
        socket.sendto(json.dumps(response).encode("utf-8"), addr)
        return
        
    server_name = message["name"]
    
    with registry_lock:
        if server_name in server_registry:
            server_info = server_registry[server_name]
            # Check if server has expired
            if time.time() - server_info["last_seen"] > SERVER_TIMEOUT:
                # Server has expired, remove it
                del server_registry[server_name]
                response = {"status": "error", "message": f"Server '{server_name}' not found"}
            else:
                # Return server info
                response = {
                    "status": "success",
                    "name": server_name,
                    "ip": server_info["ip"],
                    "port": server_info["port"]
                }
        else:
            response = {"status": "error", "message": f"Server '{server_name}' not found"}
    
    socket.sendto(json.dumps(response).encode("utf-8"), addr)

def handle_heartbeat(message, addr, socket):
    """Handle server heartbeat"""
    if "name" not in message:
        return
        
    server_name = message["name"]
    
    with registry_lock:
        if server_name in server_registry:
            # Update last seen timestamp
            server_registry[server_name]["last_seen"] = time.time()
            logger.debug(f"Heartbeat from server '{server_name}'")
            
            # Send confirmation
            response = {"status": "success"}
            socket.sendto(json.dumps(response).encode("utf-8"), addr)

def handle_list_request(addr, socket):
    """Handle request to list all available servers"""
    with registry_lock:
        current_time = time.time()
        active_servers = {}
        
        # Only include non-expired servers
        for name, info in server_registry.items():
            if current_time - info["last_seen"] <= SERVER_TIMEOUT:
                active_servers[name] = {
                    "ip": info["ip"],
                    "port": info["port"]
                }
    
    response = {
        "status": "success",
        "servers": active_servers
    }
    
    socket.sendto(json.dumps(response).encode("utf-8"), addr)

def cleanup_expired_servers():
    """Periodically remove expired servers from the registry"""
    while True:
        time.sleep(60)  # Check every minute
        
        with registry_lock:
            current_time = time.time()
            expired_servers = []
            
            # Find expired servers
            for name, info in server_registry.items():
                if current_time - info["last_seen"] > SERVER_TIMEOUT:
                    expired_servers.append(name)
            
            # Remove expired servers
            for name in expired_servers:
                logger.info(f"Removing expired server: {name}")
                del server_registry[name]

if __name__ == "__main__":
    start_registry_server()