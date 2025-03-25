# Chat applications
**Old Versions of bigger personal project**<br />
**Current version is stored in private repo and is not available to public**<br />
**Has multiple different functions that are either not implemented or are not working**<br />
**These were created to test and brainstorm different functionalities that I want to see in newer version of chat application**

## Overview
This folder contains older versions of a distributed chat application project. These versions were used to test and brainstorm different functionalities and architectural approaches for the chat application. The current version of the project is stored in a private repository and is not available to the public.

## Chat Application
A distributed chat system with a two-tier architecture:
- <code>chat/client/</code> - Client implementation with both CLI (client.py) and GUI (clientgui.py) interfaces
- <code>chat/server/</code> - Server implementation with both CLI (server.py) and GUI (servergui.py) interfaces

**Key features tested:**
- Direct client-server communication model
- Integrated authentication within the server
- Simplified deployment architecture
- Multi-threaded message handling
- Real-time notification system
- Persistent message storage

## Legacy Chat Version
An earlier implementation with a three-tier architecture:
- <code>chat version old/</code> - Contains previous architecture with separate client, server, and registry components

**Key features tested:**
- Service discovery through a dedicated registry component
- Distributed authentication system
- Load balancing capabilities
- Fault tolerance mechanisms
- Component-based modular design
- Inter-service communication protocols
- Stateless server design

## Desired Features for Newest Version
Based on the functionalities tested in these older versions, the following features are desired for the newest version of the chat application:
- **DNS Integration**: For resolving server addresses dynamically.
- **Database Integration**: For persistent storage of user data, messages, and channel information.
- **Enhanced Security**: Including robust encryption for data transmission and storage.
- **Scalability**: Ability to handle a large number of concurrent users and messages.
- **Modular Design**: To allow for easy addition and modification of features.
- **Real-time Communication**: Ensuring low-latency message delivery and notifications.
- **User Management**: Including features like user roles, permissions, and account management.
- **Channel Management**: Allowing users to create, join, and manage channels.
- **Direct Messaging**: Secure and private communication between users.
- **GUI Enhancements**: Improved user interface for better user experience.
- **Fault Tolerance**: Ensuring the system remains operational even in the event of component failures.
- **Load Balancing**: Distributing the load evenly across multiple servers to ensure optimal performance.
- **Moderation Tools**: Features for administrators to manage users and content, such as kicking users, deleting messages, and managing channels.
- **Server-Side Modularity**: A modular server architecture to facilitate the addition of new features and services without disrupting existing functionality.

These features aim to create a robust, secure, and user-friendly chat application that can scale to meet the needs of a large user base.