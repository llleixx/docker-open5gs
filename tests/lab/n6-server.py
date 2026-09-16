import socket,struct,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200);self.end_headers();self.wfile.write(('Open5GS v2.8.0 lab OK '+self.client_address[0]+'\n').encode())
    def log_message(self,*args):pass
def dns():
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('10.250.82.53',53))
    while True:
        packet,peer=sock.recvfrom(2048)
        # Lab-only A response; preserves the query question and transaction ID.
        reply=packet[:2]+b'\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00'+packet[12:]+b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'+socket.inet_aton('10.250.82.10')
        sock.sendto(reply,peer)
threading.Thread(target=dns,daemon=True).start()
HTTPServer(('10.250.82.10',8080),Handler).serve_forever()
