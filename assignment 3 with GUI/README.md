# Assignment 3 with GUI

**This isn't part of the assignment but please enjoy or test**

## Overview
This implementation enhances the basic Assignment 3 with graphical user interface elements for client component. It maintains all the core functionality of the original assignment while providing a more user-friendly experience.

## Features
- Real-time socket communication between server and multiple clients
- Graphical user interface for easier interaction
- Visual display of connected clients on server side
- User-friendly message sending and receiving interface
- Connection status indicators
- Channel-based messaging system
- Direct messaging between users
- Message history when joining channels
- Inactivity detection and automatic disconnection

## Files
- `server.py` - Enhanced server implementation with GUI elements
- `client.py` - Client implementation with graphical interface

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
1. Click the "Connect" button
2. Enter server address (format: IP:port, default 127.0.0.1:3000)
3. Enter a nickname (2-20 characters)
4. Use the interface to send messages and interact with other clients

## Client Interface
The client GUI provides:
- Connection status indicator
- Text input for sending messages
- Message history display
- Options to connect/disconnect from server
- Join channel functionality
- Direct messaging capability
- List of available channels and online users

## Commands
You can use these commands directly in the message input:
- `/join <channel>` - Join a specific channel
- `/dm <user> <message>` - Send a direct message
- `/list channels` - List all available channels
- `/list clients` - List all connected users
- `/quit` - Disconnect from the server

## Requirements
- Python 3.6+
- Tkinter (included in standard Python installation)
- Socket library (standard library)

## Differences from non-GUI version
This implementation maintains the same core socket programming concepts but adds:
- Event-driven GUI using Tkinter
- Thread management for handling GUI and socket operations simultaneously
- Visual representation of connection states and messages
- Channel management and message history
- Inactivity timeout handling

