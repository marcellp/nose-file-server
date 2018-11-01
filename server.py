import socket
import sys
import os
import os.path
import threading
import json
import tempfile
import shutil
import zlib

from collections import defaultdict

class DataStream(threading.Thread):
	def __init__(self, ip, path, checksum, size, upload=False, download=False):

		if not upload and not download:
			raise ValueError("DataStream must be initialized with either download or upload specified.")

		threading.Thread.__init__(self)

		self.ip = ip
		self.path = path

		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.s.bind(("0.0.0.0", 0))
		self.s.listen(1)

		self.port = self.s.getsockname()[1]

		self.path = path
		self.checksum = checksum
		self.size = size

		self.upload = upload
		self.download = download

		print('DATASTREAM:\tSocket for {} to send {} path launched on port {}'.format(self.ip, self.path, self.port))

	def stop(self, ret = False):
		self.c.close()
		return ret

	def run_download(self):
		while True:
			c, addr = self.s.accept()
			c.settimeout(10)

			if addr[0] != self.ip:
				print('DATASTREAM:\tData stream for {} was used by {}, breaking connection.'.format(self.ip, addr[0]))
				c.close()
			else:
				break

		self.c = c

		with open(self.path, 'rb') as f:
			while True:
				buf = f.read(1024)

				if not buf:
					break

				self.c.sendall(buf)

		self.c.close()

	def run_upload(self):
		while True:
			c, addr = self.s.accept()
			c.settimeout(10)

			if addr[0] != self.ip:
				print('DATASTREAM:\tData stream for {} was used by {}, breaking connection.'.format(self.ip, addr[0]))
				c.close()
			else:
				break

		self.c = c
		remaining_size = self.size
		recv_checksum = 0

		with tempfile.NamedTemporaryFile() as source:
			while True:
				buf = self.c.recv(1024)
				
				if not buf:
					print('DATASTREAM:\tConnection closed by remote host, stopping.')
					return self.stop()

				remaining_size -= len(buf)

				if remaining_size < 0:
					print('DATASTREAM:\tMaximum size exceeded, connection dropped.')
					return self.stop()

				recv_checksum = zlib.crc32(buf, recv_checksum)
				source.write(buf)
				source.flush()

				if remaining_size == 0:
					print('DATASTREAM:\tCorrect size received.')
					c.close()
					break

			recv_checksum = "%X" % (recv_checksum & 0xFFFFFFFF)
			recv_checksum = recv_checksum.lower()

			if recv_checksum != self.checksum:
				print('DATASTREAM:\tChecksum {} does not match sender-specified checksum {}.'.format(recv_checksum, self.checksum))
				return self.stop()

			with open(self.path, 'wb') as dest:
				source.seek(0)
				shutil.copyfileobj(source, dest)

		print('DATASTREAM:\t Temporary file {} has been successfully copied to {}.'.format(source.name, self.path))
		print('DATASTREAM:\t Closing data stream.')
		return self.stop(True)

	def run(self):
		try:
			if self.upload:
				return self.run_upload()
			
			if self.download:
				return self.run_download()
		finally:
			if self.c:
				self.c.close()

		return None

class MessageStream(threading.Thread):
	def __init__(self, c):
		threading.Thread.__init__(self)

		self.c = c
		self.addr = c.getpeername()
		self.handlers = {"list": MessageStream.list, "put": MessageStream.put, "get": MessageStream.get}

	def stop(self, ret = False):
		self.c.close()
		return ret

	def run(self):
		print('MESSAGESTREAM:\tClient from {} connected.'.format(self.addr))

		req = b""

		while True:
			req += self.c.recv(1024)

			if not req:
				print('MESSAGESTREAM:\tConnection closed by remote host, stopping.')
				return self.stop()

			if req and req[-1] == 0:
				req = req[:-1]
				req = req.decode('utf-8')
				break

		try:
			req = json.loads(req)
			cmd = req["command"].lower()
		except:
			self.error(400, "Your request could not be parsed.")
			return self.stop()

		if cmd not in self.handlers:
			self.error(400, cmd + " is not a valid command.")
			return self.stop()

		status = self.handlers[cmd](self, req)

		if status:
			print('MESSAGESTREAM:\tA {} request was successfully served to {}.'.format(cmd, self.addr))
		else:
			print('MESSAGESTREAM:\tA {} request could not be served to {}.'.format(cmd, self.addr))

		return self.stop(status)

	def send(self, msg):
		if type(msg) is dict:
			msg = json.dumps(msg)

		msg += "\x00"
		msg = msg.encode('utf-8')
		self.c.sendall(msg)
		self.c.close()
		return

	def list(self, req):
		try:
			route = req["path"].lower()
		except:
			self.error(400, "A path must be supplied.")
			return False

		route = route.lstrip(os.path.sep)
		route = os.path.join(Server.ROOT_PATH, route)
		route = os.path.realpath(route)

		if not route.startswith(Server.ROOT_PATH):
			self.error(403, "I do not take kindly to your jailbreak attempt.")
			return False

		try:
			dirs = [d for d in os.listdir(route) if os.path.isdir(os.path.join(route, d))]
			files = [f for f in os.listdir(route) if os.path.isfile(os.path.join(route, f))]
		except:
			self.error(404, "No such directory.")
			return False

		resp = {'response': 200, 'files': files, 'dirs': dirs}
		self.send(resp)

		return True

	def put(self, req):
		try:
			route = req["path"].lower()
			checksum = req["checksum"].lower()
			size = req["size"]
		except:
			self.error(400, "Required arguments missing (route, checksum and size must be supplied).")
			return False

		route = route.lstrip(os.path.sep)
		route = os.path.join(Server.ROOT_PATH, route)
		route = os.path.realpath(route)

		if not route.startswith(Server.ROOT_PATH):
			self.error(403, "I do not take kindly to your jailbreak attempt.")
			return False
		
		if os.path.isfile(route):
			self.error(403, "A file with that name already exists.")
			return False

		ip = self.addr[0]
		data_stream = DataStream(ip, route, checksum, size, upload=True)
		data_stream.start()

		resp = {"response": 200, "port": data_stream.port}
		self.send(resp)

		return True

	def get(self, req):
		try:
			route = req["path"].lower()
		except:
			self.error(400, "Required arguments missing (route must be supplied).")
			return False

		route = route.lstrip(os.path.sep)
		route = os.path.join(Server.ROOT_PATH, route)
		route = os.path.realpath(route)

		if not route.startswith(Server.ROOT_PATH):
			self.error(403, "I do not take kindly to your jailbreak attempt.")
			return False
		
		try:
			size = os.path.getsize(route)

			with open(route, "rb") as f:
				checksum = 0
				while True:
					buf = f.read(1024)

					if not buf:
						break
					checksum = zlib.crc32(buf, checksum)

			checksum = "%X" % (checksum & 0xFFFFFFFF)

		except IOError:
			self.error(404, "File at path does not exist.")
			return False


		ip = self.addr[0]
		data_stream = DataStream(ip, route, checksum, size, download=True)
		data_stream.start()

		resp = {"response": 200, "port": data_stream.port, "size": size, "checksum": checksum}
		self.send(resp)

		return True


	def error(self, code, msg = None):
		if not msg:
			msg = "Bad Request"

		err = {"response": code, "error": msg}
		self.send(err)
		return

class Server(object):
	ROOT_PATH = os.path.join(os.getcwd(), 'files/')
	ROOT_PATH = os.path.realpath(ROOT_PATH)

	def __init__(self, port, max_connections = 1):
		self.port = port
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.socket.bind(("0.0.0.0", self.port))
		self.socket.listen(max_connections)
		print('SERVER:\tServer launched on port {}'.format(self.port))

	def loop(self):
		while True:
			c, addr = self.socket.accept()
			c.settimeout(10)
			ip = addr[0]
			c_stream = MessageStream(c)
			c_stream.start()
			c_stream.join()

def main():
	usage_msg = 'Usage: {} [port]'.format(sys.argv[0])

	if len(sys.argv) != 2:
		print(usage_msg)
		return

	try:
		port = int(sys.argv[1])
	except:
		print("Invalid port")
		print(usage_msg)
		return

	s = Server(port)
	s.loop()

main()
