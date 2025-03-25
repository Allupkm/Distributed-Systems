# Distributed-Systems
This holds some of the assignments code that are graded during this course.<br />
There can be different variations of assigments so when grading read this to understand which is the correct one.<br />
Those that are part are clearly marked with bolded letters below.<br />

## Assingment 3 without GUI
This holds Assignment 3 required files, Server.py and Client.py<br />
**This Is Part of the Assignment**<br />
<code>Server.py</code> - Simple socket server implementation that handles multiple client connections<br />
<code>Client.py</code> - Client implementation for connecting to the socket server<br />

## Assignment 3 with GUI
This implementation includes a graphical user interface for both client
and server.<br />
**This Is NOT part of the assignment but feel free to use**<br />
<code>Server.py</code> - Enhanced server implementation with GUI elements<br />
<code>Client.py</code> - Client implementation with graphical interface for better user interaction<br />

## Under development
This section contains ongoing development work for distributed chat applications that explore different architectural approaches and implementation techniques.<br />
These experimental versions are separate from the assignment requirements and represent personal research into Chat application.<br />

**Everything under this is NOT part of the assignment and should not be used for grading**

### Chat Application
**Main feature was server side GUI to hold different functionalities, example kick users or delete channels**<br />
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

### Legacy Chat Version
**This was to see how can I implement different things, example more robust encryption**<br />
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
