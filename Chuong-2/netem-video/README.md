# NetEm – Video streaming dưới điều kiện mạng xấu

Chạy trên Linux (cần quyền root để dùng `tc netem`).

```bash
./setup.sh      # cài đặt môi trường
./prep.sh       # chuẩn bị video
./run_all.sh    # chạy toàn bộ kịch bản
python3 summarize.py
```
Kết quả trong [results](results).
