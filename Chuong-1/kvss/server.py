#!/usr/bin/env python3
"""
KVSS - Mini Key-Value Store Service (server)

Interface KV/1.0 (text-based line protocol over TCP):
    <version> " " <command> [ " " <args> ] "\n"
    <version> ::= "KV/1.0"
    <command> ::= "PUT" | "GET" | "DEL" | "STATS" | "QUIT"
    <args>    ::= <key> [ " " <value> ]

Responses:
    200 OK [data] | 201 CREATED | 204 NO_CONTENT | 400 BAD_REQUEST
    404 NOT_FOUND | 426 UPGRADE_REQUIRED | 500 SERVER_ERROR

Server dùng select() để multiplexing nhiều client trên một luồng.
"""
import argparse
import os
import select
import socket
import sys
import time
from datetime import datetime

VERSION = "KV/1.0"
COMMANDS = {"PUT", "GET", "DEL", "STATS", "QUIT"}
MAX_LINE = 4096  # giới hạn độ dài một dòng để tránh client gửi vô hạn không có "\n"


class KVServer:
    def __init__(self, host, port, log_path):
        self.host = host
        self.port = port
        self.store = {}            # key -> value (lưu trong bộ nhớ)
        self.start_time = time.time()
        self.served = 0            # số request đã xử lý
        self.log_file = open(log_path, "a", encoding="utf-8")
        self.buffers = {}          # sock -> bytes chưa đủ một dòng
        self.closing = set()       # sock cần đóng sau khi trả lời QUIT

    # ------------------------------------------------------------------ log
    def log(self, direction, peer, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{ts}] {peer[0]}:{peer[1]} {direction} {msg}"
        print(line, flush=True)
        self.log_file.write(line + "\n")
        self.log_file.flush()

    # -------------------------------------------------------- xử lý request
    def handle_request(self, line: str):
        """Nhận một dòng request (đã bỏ '\n'), trả về (response, quit?)."""
        self.served += 1
        if line == "":
            return "400 BAD_REQUEST", False

        parts = line.split(" ")

        # 1) Kiểm tra phiên bản trước tiên
        if parts[0] != VERSION:
            return "426 UPGRADE_REQUIRED", False
        if len(parts) < 2:
            return "400 BAD_REQUEST", False

        cmd = parts[1]
        args = parts[2:]

        # 2) Lệnh phải nằm trong tập lệnh hợp lệ
        if cmd not in COMMANDS:
            return "400 BAD_REQUEST", False

        # 3) Kiểm tra số lượng tham số đúng theo BNF (key/value không chứa
        #    khoảng trắng nên chuỗi rỗng do 2 dấu cách liền nhau cũng là lỗi)
        if any(a == "" for a in args):
            return "400 BAD_REQUEST", False

        if cmd == "PUT":
            if len(args) != 2:
                return "400 BAD_REQUEST", False
            key, value = args
            created = key not in self.store
            self.store[key] = value
            return ("201 CREATED" if created else "200 OK"), False

        if cmd == "GET":
            if len(args) != 1:
                return "400 BAD_REQUEST", False
            key = args[0]
            if key in self.store:
                return f"200 OK {self.store[key]}", False
            return "404 NOT_FOUND", False

        if cmd == "DEL":
            if len(args) != 1:
                return "400 BAD_REQUEST", False
            key = args[0]
            if key in self.store:
                del self.store[key]
                return "204 NO_CONTENT", False
            return "404 NOT_FOUND", False   # idempotent: xóa lại vẫn 404

        if cmd == "STATS":
            if args:
                return "400 BAD_REQUEST", False
            uptime = int(time.time() - self.start_time)
            return (f"200 OK keys={len(self.store)} uptime={uptime}s "
                    f"served={self.served}"), False

        if cmd == "QUIT":
            if args:
                return "400 BAD_REQUEST", False
            return "200 OK bye", True

        return "500 SERVER_ERROR", False  # không bao giờ tới đây

    # ------------------------------------------------------------- network
    def process_client(self, sock):
        peer = sock.getpeername()
        try:
            data = sock.recv(4096)
        except ConnectionError:
            data = b""
        if not data:
            self.log("--", peer, "disconnected")
            self.close_client(sock)
            return

        buf = self.buffers[sock] + data
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            raw = raw.rstrip(b"\r\x00")   # chấp nhận CRLF (và CR NUL) từ telnet
            try:
                line = raw.decode("utf-8")
                self.log("C->S", peer, repr(line))
                resp, quit_ = self.handle_request(line)
            except UnicodeDecodeError:
                self.log("C->S", peer, f"<invalid utf-8 {raw!r}>")
                resp, quit_ = "400 BAD_REQUEST", False
            except Exception as e:           # lỗi nội bộ không lường trước
                self.log("!!", peer, f"exception: {e!r}")
                resp, quit_ = "500 SERVER_ERROR", False

            self.log("S->C", peer, repr(resp))
            try:
                sock.sendall((resp + "\n").encode("utf-8"))
            except OSError:
                self.close_client(sock)
                return
            if quit_:
                self.close_client(sock)
                return

        if len(buf) > MAX_LINE:               # dòng quá dài, không có LF
            self.log("S->C", peer, "'400 BAD_REQUEST' (line too long)")
            sock.sendall(b"400 BAD_REQUEST\n")
            buf = b""
        self.buffers[sock] = buf

    def close_client(self, sock):
        self.buffers.pop(sock, None)
        try:
            sock.close()
        except OSError:
            pass

    def serve_forever(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(16)
        srv.setblocking(False)
        self.log("--", (self.host, self.port), f"KVSS server listening (pid={os.getpid()})")

        try:
            while True:
                readable, _, _ = select.select([srv] + list(self.buffers), [], [])
                for s in readable:
                    if s is srv:
                        conn, addr = srv.accept()
                        conn.setblocking(False)
                        self.buffers[conn] = b""
                        self.log("--", addr, "connected")
                    else:
                        self.process_client(s)
        except KeyboardInterrupt:
            self.log("--", (self.host, self.port), "server shutting down")
        finally:
            for s in list(self.buffers):
                self.close_client(s)
            srv.close()
            self.log_file.close()


def main():
    ap = argparse.ArgumentParser(description="KVSS server (KV/1.0)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5050)
    ap.add_argument("--log", default="server.log", help="đường dẫn file log")
    a = ap.parse_args()
    KVServer(a.host, a.port, a.log).serve_forever()


if __name__ == "__main__":
    main()
