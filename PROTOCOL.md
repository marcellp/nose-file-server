Mixed-State File Transfer Protocol
==================================

*by Marcell Pek (2333134P) and Myles Lamb (2325727L)*

This is the official specification for the Mixed-State File Transfer Protocol (MSFTP). A reference client and server implementation has been provided for this protocol.

Aims
----

The goals of MSFTP are to:

* provide a stateless message exchange protocol for fast and reliable exchange of metadata;
* provide a stateful data exchange protocol to transfer data reliably and efficiently across devices on different networks.

The goals of the MSFTP exchange protocols are to:
* have little code footprint on modern programming languages;
* be backwards-compatible and extensible for future versions;
* be easily implementable in a safe and secure manner.

Terminology
-----------

* **UTF-8**: the UTF-8 transformation format is as defined in RFC 3629;
* **JSON**: the JSON Data Exchange Standard as defined by ECMA-404;
* **byte**: a byte, when used in this document, refers to the size of the data unit used to transmit information between the client and the server. A byte, in this context, is defined to be an octet (i.e. 8 bits). This does not establish a limitation on the individual systems to store, interpret, or process data with byte or word sizes different to this format;
* **message exchange connection**: the connection over which control messages and metadata are exchanged between the client and the server;
* **data exchange connection**: the connection over which files or other data are exchanged between the client and the server;
* **request**: a message sent by the client through the message exchange connection;
* **response**: a message sent by the server through the message exchange connection;
* **message**: a message sent through the message exchange connection;
* **file**: data that is to be exchanged between the client and the server through the data exchange connection;
* **user**: a person wishing to obtain file exchange services from a server providing MSFTP services.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED",  "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

Model
-----

In MSFTP, the user wishing to exchange messages with the service uses a client that MAY provide an additional abstraction level to shield the user from the actual implementation of this protocol. When the user indicates that a request is to be sent, the client connects to the MSFTP service and sends the message via the message exchange connection. The server then sends a standard response to this request via the same message exchange connection and closes the connection.

When the user indicates that a file is to be transferred to or from the MSFTP service, the service establishes an ephemeral data exchange connection for the exclusive use of the user and sends information in the response that is needed for the user or the client to utilize this connection. The user then connects to the data exchange connection using the information supplied and, depending on the direction of the exchange, listens for an incoming file or sends a file. The sending party closes the connection at the end of the transmission.

Message-exchange connection
---------------------------

The message exchange connection is established as a TCP connection from the client to the server. The standard service port for MSFTP is 6969. The client is responsible for sending requests to the service and the service is responsible for sending appropriate replies to requests.

All messages MUST contain all the elements of the following general data format:
* the *payload*, which is a singular JSON object whose textual representation may contain Unicode characters. The payload is encoded into bytes using UTF-8 before transmission;
* and the ``NULL`` character, which terminates all messages, represented as the numerical value zero (note that this is different from the JSON-value ``null``).

All requests are messages whose payload:
* MUST contain the property ``command``, which SHOULD be a lower-case keyword and SHOULD be defined by this standard.

All responses are messages whose payload:
* MUST contain the property ``response``, which MUST be a JSON integer corresponding to a status code as defined by Section 10 of RFC 2616;
* if a status code classified as an *error* by RFC 2616 is provided, a property ``error`` SHOULD be provided, which MUST be a JSON string and SHOULD contain a human-readable description for the error;
* MUST NOT contain an ``error`` property if the value of the ``response`` property does not correspond to an *error* as defined by RFC 2616.

Message-exchange connections are stateless and are not kept alive. When a client wishes to send a request to the server, a connection is opened and a request message is sent per these specifications. The service constructs an appropriate response per these specifications and closes the connection immediately.

When designing new message-exchange commands, and in the implementation of existing message-exchange commands, the server MUST NOT keep observable state and requests MUST NOT have observable side effects from the perspective of the client receiving a response from the service.

A message is incomplete if some or all of its constituent components are missing. When receiving messages, a party MUST NOT accept messages that are not ``NULL``-terminated, even if the message contains a valid payload. Each party MAY decide to drop the connection if a message appears to be incomplete for longer than is deemed acceptable.

Message-exchange commands
-------------------------

The ``command`` property of message-exchange request objects SHOULD be one of the following:

### list

The sender of this command indicates that they wish to receive information about the contents of the file server. A request of this type MUST contain the propety ``path``, which MUST be a JSON string and MUST contain a relative URI as defined by RFC 3986.

The response for this request, if successful, MUST contain a ``files`` and ``dirs`` property. These properties MUST be JSON lists and they typically corresponds to the files and directories that the service makes available at ``path``. Both ``files`` and ``dirs`` MAY be empty lists, especially if the implementation does not support recursive directory access.

### put

The sender of this command indicates that it wishes to send a file to the service. A request of this type MUST contain the property ``path``, ``checksum`` and ``size``. ``path`` MUST be a JSON string and MUST contain a relative URI as defined by RFC 3986, and contains the path to the file to be sent to the service. ``size`` MUST be a JSON integer corresponding to the size of the file to be transferred in bytes. ``checksum`` MUST be a JSON string corresponding to the big-endian hexadecimal representation of the file's CRC-32 checksum as defined in ITU-T V.42. ``checksum`` as a string SHOULD consist of upper case characters.

The response for this request, if successful, MUST contain a ``port`` property, which MUST correspond to an open TCP port at the server's current network address, which the client can connect to and write the contents of the file to.

### get

The sender of this command indicates it wishes to retrieve a file from the service. A request of this type MUST contain the property ``path``. ``path`` MUST be a JSON string and MUST contain a relative URI as defined by RFC 3986, and contains the path to the file on the server that is to be sent to the client.

The response for this request, if successful, MUST contain a ``port``, ``size`` and ``checksum``. property. ``port``  MUST correspond to an open TCP port at the server's current network address, which the client can connect to and read the contents of the file from. ``size`` MUST be a JSON integer corresponding to the size of the file to be transferred in bytes. ``checksum`` MUST be a JSON string corresponding to the big-endian hexadecimal representation of the file's CRC-32 checksum as defined in ITU-T V.42. ``checksum`` as a string SHOULD consist of upper case characters.

Data-exchange connection
------------------------

The data exchange connection is used to send files between the client and the server. This data-exchange connection is established as a TCP connection from the client to the server at the port specified in the response to the ``get`` and ``put`` requests of the client. A data-exchange connection is stateful in that the port number at which the connection is open is defined by the information a client sent in the ``put`` or ``get`` requests.

When a client retrieves the port information for a ``put``/``get`` connection, the client MUST connect to the server at the given port as soon as possible. If a client cannot connect to the port number, it SHOULD assume a timeout has occurred.

When a client has connected to a data-exchange connection for a ``put`` request, the client MUST send the contents of the file as a a stream of bytes. When a client has successfully sent all the data in the file, the client MUST close the connection to indicate to the server that the file transfer is complete. When the server receives the number of bytes from the stream as defined by the ``size`` attribute of the ``put`` request object, the server MUST assume that the file has been successfuly transferred. If the server encounteres more data in the stream than the ``size`` attribute of the ``put`` object indicates, the server MUST drop the connection. The server MAY assume that the first ``size`` bytes of the transmission were correct. After the data has been successfully transferred, the server MUST compare the checksum recieved in the ``checksum`` field of the corresponding request to the checksum of the data stream received. If there is a mismatch, the server MUST mark the transfer as invalid and MUST NOT make the file available through the service.

When a client has connected to a data-exchange connection for a ``get`` request, the service MUST send the contents of the file as a a stream of bytes. When the service has successfully sent all the data in the file, the service MUST close the connection to indicate to the server that the file transfer is complete. When the client receives the number of bytes from the stream as defined by the ``size`` attribute of the ``get`` response object, the client MUST assume that the file has been successfuly transferred. If the client encounteres more data in the stream than the ``size`` attribute of the ``put`` object indicates, the client MUST drop the connection. The client MAY assume that the first ``size`` bytes of the transmission were correct. After the data has been successfully transferred, the client MUST compare the checksum recieved in the ``checksum`` field of the corresponding response to the checksum of the data stream received. If there is a mismatch, the client MUST mark the transfer as invalid and MUST NOT make the file available to the user.

Design considerations
---------------------

We have decided to implement a protocol that blends some elements of HTTP and FTP. The design philosophies behind HTTP were used to implement the message-exchange connection and the design philosophies of FTP's file transfer facility were used to implement the data-exchange protocol. This design proves to be very easy and efficient to implement and use. The design is fast, lightweight and resilient to most error conditions. 

A potential issue with this design is that although errors should always be caught and handled, these errors are not always communicated to the client, particularly when there has been an error during the data-exchange process (i.e. the server could not create a temporary file or copy the contents to the final destination, there has been a checksum verification error, etc.). Although error recovery for errors on the client side has never been a priority, if a server error occurred during the data-exchange process the only way the client will be made aware of it is if it queries the server for the state of the path that it wanted to send data to. We believe this issue is not something that should manifest itself too often -- it should only be triggered by conditions that are out of the control of the server.

As for the implementations, the server uses Python threading so it can provide support for multiple concurrent connections. This makes the system somewhat resiliant in that the unexpected failure of a thread keeps the service running. There are certainly cases where unhandled exceptions may occur within the code, and in the message-exchange part of the code this may lead to sockets being not freed by the program. This may be an issue in some special edge cases but the server should still keep running because of the way in which it is implemented.

Running the reference implementation
------------------------------------
### Server
The server can be run by

``python3 server.py PORT``

where PORT is the transport layer address of the service being used.

### Client
The client can be run with any of the following commands

* ``python3 Client.py HOSTNAME PORT list <PATH>``  
* ``python3 Client.py HOSTNAME PORT get LOCAL_FILENAME <REMOTE_FILENAME>``
* ``python3 Client.py HOSTNAME PORT put REMOTE_FILENAME <LOCAL_FILENAME>``

``HOSTNAME`` denotes the IP address of the system running the server implementation.

``<>`` denotes an optional arguement. In the case of ``list`` the default directory of the server's file path will be returned. In the case of ``get`` and ``put`` the filename of the non-optional arguement will be used.
