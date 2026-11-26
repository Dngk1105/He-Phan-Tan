#!/usr/bin/env python3
"""
KVSS - client dòng lệnh.

Đọc từng dòng từ stdin, gửi tới server theo chuẩn KV/1.0 và in nguyên văn
status + data mà server trả về.

Mặc định: nếu dòng nhập không bắt đầu bằng "KV/1.0" thì client tự thêm
tiền tố để tuân thủ Interface (người dùng chỉ cần gõ "PUT k v").
Dùng --raw để gửi nguyên văn (phục vụ kiểm thử các ca sai giao thức).
"""
import argparse
import socket
import sys

VERSION = "KV/1.0"


def recv_line(f):
    """Đọc một dòng (kết thúc bằng \\n) từ file-object của socket."""
    line = f.readline()
    if not line:
        return None
    return line.decode("utf-8").rstrip("\n")


def main():
    ap = argparse.ArgumentParser(description="KVSS client (KV/1.0)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5050)
    ap.add_argument("--raw", action="store_true",
                    help="gửi nguyên văn, không tự thêm tiền tố KV/1.0")
    a = ap.parse_args()

    interactive = sys.stdin.isatty()
    try:
        sock = socket.create_connection((a.host, a.port))
    except OSError as e:
        print(f"Không kết nối được {a.host}:{a.port}: {e}", file=sys.stderr)
        sys.exit(1)

    rf = sock.makefile("rb")
    if interactive:
        print(f"Đã kết nối {a.host}:{a.port}. Gõ lệnh (PUT/GET/DEL/STATS/QUIT), Ctrl-D để thoát.")

    try:
        for line in sys.stdin:
            line = line.rstrip("\r\n")
            if line == "" and interactive:
                continue
            if not a.raw and not line.startswith(VERSION):
                line = f"{VERSION} {line}"
            if not interactive:
                print(f"C: {line}")
            sock.sendall((line + "\n").encode("utf-8"))

            resp = recv_line(rf)
            if resp is None:
                print("(server đã đóng kết nối)")
                break
            print(f"S: {resp}" if not interactive else resp)
            if resp == "200 OK bye":
                break
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


if __name__ == "__main__":
    main()
