# KVSS – Mini Key–Value Store Service (KV/1.0)

Bài thực hành Chương 1 – Interface trong hệ thống phân tán.

```
kvss/
├── server.py                 # TCP server, select() multiplexing, log có timestamp
├── client.py                 # client dòng lệnh, đọc stdin, in nguyên văn phản hồi
├── test_kvss.py              # 13 ca kiểm thử (hợp lệ + lỗi), tự spawn server ở cổng 5051
├── test_results.txt          # kết quả chạy test
├── server.log                # log của server (request/response + timestamp)
└── capture/
    ├── kvss_session.pcapng          # gói tin bắt bằng Wireshark/tshark
    └── kvss_session_analysis.txt    # packet list + Follow TCP Stream
```

## 1. Chạy server

```bash
python3 server.py                       # 127.0.0.1:5050, log -> server.log
python3 server.py --host 0.0.0.0 --port 5050 --log server.log
```

## 2. Chạy client

```bash
python3 client.py                       # gõ PUT k v / GET k / DEL k / STATS / QUIT
python3 client.py --raw                 # gửi nguyên văn (để thử ca thiếu version…)
printf "PUT a 1\nGET a\nQUIT\n" | python3 client.py
```

Mặc định client tự thêm tiền tố `KV/1.0` nếu người dùng gõ thiếu; `--raw` tắt tính năng này.

## 3. Kiểm thử tự động

```bash
python3 test_kvss.py                    # tự chạy server cổng 5051
python3 test_kvss.py --no-spawn --port 5050   # dùng server đang chạy
```

## 4. Tương tác thủ công

```bash
nc 127.0.0.1 5050
telnet 127.0.0.1 5050
printf "KV/1.0 PUT city Hanoi\nKV/1.0 GET city\nKV/1.0 QUIT\n" | nc -q1 127.0.0.1 5050
```

## 5. Bắt gói bằng Wireshark

**Cách A – Wireshark trên Windows (đã dùng để tạo `capture/kvss_session.pcapng`)**

WSL2 là máy ảo riêng nên Wireshark Windows không thấy loopback bên trong WSL.
Cho server bind `0.0.0.0`, client chạy từ Windows nối tới IP của WSL (`ip -4 addr show eth0`),
gói đi qua adapter `vEthernet (WSL)`:

```powershell
# Windows PowerShell
& "C:\Program Files\Wireshark\tshark.exe" -D                      # xem số thứ tự adapter vEthernet (WSL)
& "C:\Program Files\Wireshark\tshark.exe" -i <N> -f "tcp port 5050" -w kvss_session.pcapng
# Wireshark GUI: chọn adapter "vEthernet (WSL)", capture filter: tcp port 5050
```

Phân tích offline:

```powershell
& "C:\Program Files\Wireshark\tshark.exe" -r kvss_session.pcapng
& "C:\Program Files\Wireshark\tshark.exe" -r kvss_session.pcapng -q -z follow,tcp,ascii,0
```

**Cách B – Wireshark ngay trong WSL (WSLg)**

```bash
sudo apt install -y wireshark tshark          # chọn "Yes" cho non-root capture
sudo usermod -aG wireshark $USER && newgrp wireshark
wireshark &                                    # chọn interface "lo", filter: tcp.port == 5050
```

## 6. Quy tắc phản hồi (tóm tắt cài đặt)

| Tình huống | Mã |
|---|---|
| PUT key mới | `201 CREATED` |
| PUT key đã có (ghi đè) | `200 OK` |
| GET key có | `200 OK <value>` |
| GET / DEL key không có | `404 NOT_FOUND` |
| DEL key có | `204 NO_CONTENT` |
| STATS | `200 OK keys=N uptime=Ns served=M` |
| QUIT | `200 OK bye` rồi server đóng kết nối |
| Thiếu / sai `KV/1.0` | `426 UPGRADE_REQUIRED` |
| Lệnh lạ, thiếu/thừa tham số, dòng rỗng, UTF-8 hỏng | `400 BAD_REQUEST` |
| Exception nội bộ | `500 SERVER_ERROR` |

Thứ tự kiểm tra: **version → command → args**. Dòng nhận được sẽ bỏ `\r` (và `\0`) ở cuối để tương thích telnet.
