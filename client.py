import sys
import json
import socket
import os
import zlib
import tempfile
import shutil



class Client:

    def __init__(self, args):
        """
            args[0],args[1] : ip,port number
            args[2],args[3] : request type,parameter(s)
        """

        self.requests = {"put": self.format_put,
                         "get": self.format_get,
                         "list": self.format_list}
        self.server_id = ""
        self.port = 0
        self.format_args(args)
        self.requests[args[2]](args[3:])

    def format_args(self, args):
        """assures whether the arguments are of the correct form
            adds default empty string if no arg is provided"""

        fail_state = False

        if len(args) < 3 or len(args) > 5:
            print("ERROR: ARG LENGTH\n\tEXPECTED [3,4]\n\tGOT: {}".format(len(args)))
            sys.exit() #prevent an out of bounds


        #default arguement so we dont need to validate later
        if len(args) == 3:
            args.append("")

        if args[1].isdigit():
           self.port = int(args[1])
        else:
           print("ERROR: PORT NUMBER\n"
                  "\tEXPECTED INTEGER GOT \"{}\" ".format(args[1]))
           fail_state = True



        if args[2] not in self.requests:
            print("unrecognised request type: \n"
                  "\t EXPECTED {} GOT \"{}\"".format(", ".join(self.requests.keys()), args[2]))
            fail_state = True
        self.server_id = args[0]
        if fail_state:
            sys.exit()

    def socket_factory(self, server=None, port=None):
        """returns none if the host to the host could not be made"""

        if not server:
            server = self.server_id
        if not port:
            port = self.port

        print("attempt connection on: (IP) {} (Port) {}".format(server,port), end="\n\n")
        cli_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli_sock.settimeout(0.1)
        try:
            cli_sock.connect((server, port))
        except:
            return None
        return cli_sock

    def format_put(self, args):
        """returns a formatted put request as json"""
        print(args)
        if args == [""]:
            print("usage; put [filename] (remote filename)")
            return None

        try:
            file_size = os.path.getsize(args[0])
            print(file_size)
        except:
            print("The requested file could not be found")
            return None


        with open(args[0], "rb") as f:
            crc_checksum = self.compute_checksum(f)
            print(crc_checksum)

        #arrange for the file to be transferred
        payload = {"command": "put", "path": args[0],"checksum":crc_checksum,"size":file_size}
        payload = json.dumps(payload) + "\x00"

        # this should be a port number
        response = self.send_request(payload)
        print(response)

        if not response:

            return None

        self.send_file(args[0], port=response["port"])



        pass

    def compute_checksum(self,file):
        """utility for verifying file integrity"""

        crc_checksum = 0
        for line in file:
            crc_checksum = zlib.crc32(line, crc_checksum)
        return"%X" % (crc_checksum & 0xFFFFFFFF)


    def format_get(self, args):
        """returns a formatted get request as json"""
        if len(args) != 2:
            print("EXPECTED target and dest file\nGOT: {}".format(", ".join(args)))



        payload = {"command":"get","path":args[0]}
        payload = json.dumps(payload) + "\x00"


        response = self.send_request(payload)

        if not response:
            return None
        filepath = args[1]
        self.receive_file(response, filepath)

    def receive_file(self,response,filepath):

        connection = self.socket_factory(port=response["port"])

        size = int(response["size"])
        checksum = response["checksum"].lower()
        recv_checksum = 0

        with tempfile.NamedTemporaryFile() as file:
            while True:
                buf = connection.recv(1024)

                if not buf:
                    #will be triggered on null response
                    print('Connection to server was closed')
                    connection.close()
                    return

                size -= len(buf)

                if size < 0:
                    print('DATASTREAM:\tMaximum size exceeded, connection dropped.')
                    connection.close()
                    return

                recv_checksum = zlib.crc32(buf, recv_checksum)
                file.write(buf)
                file.flush()

                if size == 0:
                    print('DATASTREAM:\tCorrect size received.')
                    connection.close()
                    break

            #compute a checksum on only part of the data
            recv_checksum = "%X" % (recv_checksum & 0xFFFFFFFF)
            recv_checksum = recv_checksum.lower()

            if recv_checksum != checksum:
                print('DATASTREAM:\tChecksum {} does not match sender-specified checksum {}.'
                      .format(recv_checksum,checksum))
                connection.close()
                return None

            #commit to non temporary file
            file.seek(0)
            with open(filepath,"wb") as dest_file:
                shutil.copyfileobj(file,dest_file)

    def format_list(self, args):
        """formats and sends list request"""

        if not args:
            args.append("/")
        payload = {"command": "list", "path": args[0]}
        payload = json.dumps(payload) + "\x00"

        response = self.send_request(payload)
        print("\n\n")
        if response:
            print("RESPONSE:\"", args[0], "\"")
            for dir in response["dirs"]:
                print("<DIR> ".rjust(10, ' '), dir)
            for file in response["files"]:
                print("<FILE> ".rjust(10, ' '), file)
            return True
        return None

    def send_file(self,file_name,ip=None, port = None):

        send_socket = self.socket_factory(server=ip,port=port)
        with open(file_name,"rb") as f:
            while True:

                buffer = f.read(1024)
                send_socket.sendall(buffer)
                if not buffer:
                    break
        print("REQUEST SENT (IP){} (PORT){}".format(self.server_id,self.port))

        pass

    def send_request(self, payload):
        """standard method for sending request, returns the response to the calling method"""

        client_socket = self.socket_factory()
        if not client_socket:
            print("ERROR: connection to host failed")
            sys.exit()

        client_socket.sendall(payload.encode("utf-8"))
        print("REQUEST: SENT",payload)

        nullPresent = False
        response = b""

        while not nullPresent:
            response += client_socket.recv(1024)
            if not response:
                return None
            if response[-1] == 0:
                nullPresent = True

        # strip off the null byte
        response = response[:-1].decode("utf-8")
        response = json.loads(response)

        if response["response"] != 200:
            self.error_handler(response)
            return None

        return response

    def error_handler(self, response):
        print("Error code: ", response["response"])
        print("\t", response["error"])

        return None





if __name__ == "__main__":
    #filter off filename
    client_obj = Client(sys.argv[1:])


