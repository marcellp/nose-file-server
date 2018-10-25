import sys
import json
import socket
import os
import zlib


class Client:

    def __init__(self, args):
        """
            args[0],args[1] : ip,port number
            args[2],args[3] : request type,parameter
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
            print("Unrecognised argument length")
            sys.exit() #prevent an out of bounds


        #default arguement so we dont need to validate later
        if len(args) == 3:
            args.append("")

        if args[1].isdigit():
           self.port = int(args[1])
        else:
           print("Port number not recognised:\n"
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
            return False

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
        print("hello")

        if not response:

            return None

        #file_transfer = self.socket_factory(port=response["port"])
        self.send_file(args[0], port=response["port"])



        pass

    def compute_checksum(self,file):
        crc_checksum = 0
        for line in file:
            crc_checksum = zlib.crc32(line, crc_checksum)
        return"%X" % (crc_checksum & 0xFFFFFFFF)


    def format_get(self, args):
        """returns a formatted get request as json"""

        payload = {"command":"get","path":args[0]}
        payload = json.dumps(payload) + "\x00"
        response = self.send_request(payload)

        if response:
            #download the file
            pass

        pass

    def format_list(self, args):
        """returns a formatted list request as json"""

        if not args:
            args.append("/")
        payload = {"command": "list", "path": args[0]}
        payload = json.dumps(payload) + "\x00"

        response = self.send_request(payload)
        print("\n\n")
        if response:
            print("response for path:\"", args[0], "\"")
            for dir in response["dirs"]:
                print("<DIR> ".rjust(10, ' '), dir)
            for file in response["files"]:
                print("<FILE> ".rjust(10, ' '), file)

        return True

    def send_file(self,file_name,ip=None, port = None):

        send_socket = self.socket_factory(server=ip,port=port)
        with open(file_name,"rb") as f:
            while True:

                buffer = f.read(1024)
                send_socket.sendall(buffer)
                if not buffer:
                    break
        print("File has been sent to host (IP){} (PORT){}".format(self.server_id,self.port))

        pass

    def send_request(self, payload):
        """standard method for sending request, returns the response to the calling method"""

        client_socket = self.socket_factory()

        if not client_socket:
            print("An error occured while trying to connect to the host")
            sys.exit()

        client_socket.sendall(payload.encode("utf-8"))
        print(payload, " sent waiting for response...")

        nullPresent = False
        response = b""

        while not nullPresent:
            response += client_socket.recv(1024)
            if response[-1] == 0:
                nullPresent = True

        # strip off the null byte
        response = response[:-1].decode("utf-8")
        response = json.loads(response)

        if response["response"] != 200:
            self.error_handler(response)
            return False

        return response

    def error_handler(self, response):
        print("Error code: ", response["response"])
        print("\t", response["error"])

        pass


if __name__ == "__main__":
    client_obj = Client(sys.argv[1:])

# do validation not in main but somewhere in the actual object###
# use format methods to send all the thingies out of one function
# have a look at parsing filenames etc, make sure that this is safe and cannot leak outside
