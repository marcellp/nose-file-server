Mixed-State File Transfer Protocol
==================================

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
