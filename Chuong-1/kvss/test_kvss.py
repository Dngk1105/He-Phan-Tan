#!/usr/bin/env python3
"""
Bộ kiểm thử KVSS - 10 ca (hợp lệ + lỗi).

Cách chạy:   python3 test_kvss.py            (tự khởi động server ở cổng 5051)
             python3 test_kvss.py --port 5050 --no-spawn   (dùng server đang chạy)
"""
import argparse
import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def send(sock, raw: bytes) -> str:
    """Gửi bytes nguyên văn, đọc về một dòng phản hồi."""
    sock.sendall(raw)
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            return "<closed>"
        buf += chunk
    return buf.decode("utf-8").rstrip("\n")


def connect(host, port):
    s = socket.create_connection((host, port))
    s.settimeout(3)
    return s


def build_cases():
    """Mỗi ca: (tên, request gửi đi, kỳ vọng). request có thể là list để gửi
    nhiều dòng liên tiếp (chỉ so sánh phản hồi cuối cùng)."""
    return [
        # ---- ca hợp lệ ----
        ("TC01 PUT tạo mới",             b"KV/1.0 PUT user42 Alice\n",     "201 CREATED"),
        ("TC02 GET key có",              b"KV/1.0 GET user42\n",           "200 OK Alice"),
        ("TC03 PUT ghi đè key đã có",    b"KV/1.0 PUT user42 Bob\n",       "200 OK"),
        ("TC04 DEL key có",              b"KV/1.0 DEL user42\n",           "204 NO_CONTENT"),
        ("TC05 DEL lại (idempotent)",    b"KV/1.0 DEL user42\n",           "404 NOT_FOUND"),
        ("TC06 GET key không tồn tại",   b"KV/1.0 GET nokey\n",            "404 NOT_FOUND"),
        # ---- ca lỗi ----
        ("TC07 Thiếu version",           b"PUT user42 Alice\n",            "426 UPGRADE_REQUIRED"),
        ("TC08 Sai version",             b"KV/2.0 GET user42\n",           "426 UPGRADE_REQUIRED"),
        ("TC09 PUT thiếu value",         b"KV/1.0 PUT user42\n",           "400 BAD_REQUEST"),
        ("TC10 Lệnh không tồn tại",      b"KV/1.0 POTT user42 Alice\n",    "400 BAD_REQUEST"),
        # ---- bổ sung ----
        ("TC11 STATS",                   b"KV/1.0 STATS\n",                "200 OK keys="),
        ("TC12 Request bị chia 2 gói",   [b"KV/1.0 PUT sp", b"lit 123\n"],   "201 CREATED"),
        ("TC13 QUIT",                    b"KV/1.0 QUIT\n",                 "200 OK bye"),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5051)
    ap.add_argument("--no-spawn", action="store_true", help="không tự chạy server")
    a = ap.parse_args()

    proc = None
    if not a.no_spawn:
        proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "server.py"),
             "--port", str(a.port), "--log", os.path.join(HERE, "test_server.log")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)

    passed = failed = 0
    rows = []
    try:
        sock = connect(a.host, a.port)
        for name, req, expect in build_cases():
            if isinstance(req, list):
                for part in req[:-1]:
                    sock.sendall(part)
                    time.sleep(0.2)          # ép TCP gửi thành 2 segment
                got = send(sock, req[-1])
                shown = b"".join(req)
            else:
                got = send(sock, req)
                shown = req
            ok = got.startswith(expect)
            passed += ok
            failed += (not ok)
            rows.append((name, shown.decode().rstrip("\n"), expect, got, "PASS" if ok else "FAIL"))
        sock.close()
    finally:
        if proc:
            proc.terminate()
            proc.wait()


    # In kết quả
    headers = ("Test case", "Request", "Kỳ vọng", "Thực tế", "KQ")

    # Tính độ rộng từng cột
    widths = [
        max(len(str(row[i])) for row in rows + [headers])
        for i in range(len(headers))
    ]

    # Khung bảng
    def separator(char="-"):
        return "+" + "+".join(char * (width + 2) for width in widths) + "+"

    def format_row(row):
        return "| " + " | ".join(
            str(value).ljust(widths[i])
            for i, value in enumerate(row)
        ) + " |"

    print()
    print("KẾT QUẢ TEST")
    print(separator("="))
    print(format_row(headers))
    print(separator("="))

    for row in rows:
        print(format_row(row))

    print(separator("-"))
    print(f"PASS: {passed}  |  FAIL: {failed}")
    print()

    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
