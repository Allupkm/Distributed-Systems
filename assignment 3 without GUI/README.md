# Assignment 3 without GUI

**This is Part of the Assignment**

## Overview
This is a simple distributed chat application that demonstrates socket-based client-server communication. The implementation allows multiple clients to connect to a central server, join different channels, and exchange messages in real-time.

## Features
- Multiple client connections using sockets and threading
- Channel-based messaging system
- Direct messaging between users
- Message history when joining channels
- Inactivity detection and automatic disconnection
- Command-based interaction

## Files
- `server.py` - Simple socket server implementation that handles multiple client connections
- `client.py` - Client implementation for connecting to the socket server

## How to Run

### Server
Run the server first:
The server will start and display connection information in the console:
- The server listens on all interfaces (0.0.0.0) on port 3000 by default
- Local IP address for network connections will be displayed
- For local testing, clients can connect to 127.0.0.1:3000

### Client
Run one or more client instances:
When the client starts:
1. Enter server address (format: IP:port, default 127.0.0.1:3000)
2. Enter a nickname (2-20 characters)
3. Use the terminal to send messages and commands

## Commands
You can use these commands in the client:
- `/join <channel>` - Join a specific channel
- `/dm <user> <message>` - Send a direct message
- `/list channels` - List all available channels
- `/list clients` - List all connected users
- `/quit` - Disconnect from the server
- `/help` - Show available commands
- `None` - To message current channel just type the message and press enter  

## Requirements
- Python 3.6+
- Socket library (standard library)
- Threading library (standard library)
