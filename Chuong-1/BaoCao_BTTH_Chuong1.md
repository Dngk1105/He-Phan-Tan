# BÁO CÁO BÀI THỰC HÀNH CHƯƠNG 1 – TỔNG QUAN VÀ KIẾN TRÚC HPT

Môi trường: Windows 11 + WSL2 Ubuntu 24.04, Python 3.12, `nc`, `telnet`, Wireshark 4.x (Windows).
Mã nguồn: `~/Hệ Phân Tán/Chap1/kvss/` (WSL).

---

## PHẦN 1 – INTERFACE: MINI KEY–VALUE STORE SERVICE (KVSS)

### 1.1. Thiết kế

| Thành phần | Cài đặt |
|---|---|
| `server.py` | TCP server một luồng, dùng `select()` để multiplexing nhiều client; lưu KV trong `dict`; ghi log mọi request/response kèm timestamp (ms) ra stdout và `server.log`; buffer theo từng client để ghép đủ một dòng (`\n`) mới xử lý. |
| `client.py` | Đọc stdin từng dòng, gửi tới server, in nguyên văn status + data. Tự thêm tiền tố `KV/1.0` nếu thiếu; cờ `--raw` để gửi nguyên văn (phục vụ test ca lỗi). |
| `test_kvss.py` | 13 ca kiểm thử tự động (tự spawn server ở cổng 5051). |

Thứ tự kiểm tra request trong server: **(1) version → (2) command → (3) số lượng tham số**. Sai ở bước nào trả mã lỗi tương ứng (`426` → `400`).

Quy tắc trả mã (những chỗ đề không nói rõ, nhóm tự quy định):
- PUT key **mới** → `201 CREATED`; PUT **ghi đè** key đã có → `200 OK`.
- `key`, `value` không chứa khoảng trắng (đúng BNF `1*VCHAR`); thừa/thiếu tham số → `400`.
- Sau `QUIT` server trả `200 OK bye` rồi chủ động đóng kết nối.
- Dòng rỗng, lệnh lạ, UTF-8 hỏng → `400 BAD_REQUEST`.

### 1.2. Kết quả kiểm thử (`python3 test_kvss.py`)

| Test case | Request | Kỳ vọng | Thực tế | KQ |
|---|---|---|---|---|
| TC01 PUT tạo mới | `KV/1.0 PUT user42 Alice` | 201 CREATED | 201 CREATED | PASS |
| TC02 GET key có | `KV/1.0 GET user42` | 200 OK Alice | 200 OK Alice | PASS |
| TC03 PUT ghi đè key đã có | `KV/1.0 PUT user42 Bob` | 200 OK | 200 OK | PASS |
| TC04 DEL key có | `KV/1.0 DEL user42` | 204 NO_CONTENT | 204 NO_CONTENT | PASS |
| TC05 DEL lại (idempotent) | `KV/1.0 DEL user42` | 404 NOT_FOUND | 404 NOT_FOUND | PASS |
| TC06 GET key không tồn tại | `KV/1.0 GET nokey` | 404 NOT_FOUND | 404 NOT_FOUND | PASS |
| TC07 Thiếu version | `PUT user42 Alice` | 426 UPGRADE_REQUIRED | 426 UPGRADE_REQUIRED | PASS |
| TC08 Sai version | `KV/2.0 GET user42` | 426 UPGRADE_REQUIRED | 426 UPGRADE_REQUIRED | PASS |
| TC09 PUT thiếu value | `KV/1.0 PUT user42` | 400 BAD_REQUEST | 400 BAD_REQUEST | PASS |
| TC10 Lệnh không tồn tại | `KV/1.0 POTT user42 Alice` | 400 BAD_REQUEST | 400 BAD_REQUEST | PASS |
| TC11 STATS | `KV/1.0 STATS` | 200 OK keys=… | 200 OK keys=0 uptime=0s served=11 | PASS |
| TC12 Request bị chia 2 gói TCP | `KV/1.0 PUT sp` + `lit 123\n` | 201 CREATED | 201 CREATED | PASS |
| TC13 QUIT | `KV/1.0 QUIT` | 200 OK bye | 200 OK bye | PASS |

**PASS: 13 / FAIL: 0.**

### 1.3. Tương tác thủ công bằng nc / telnet

```
$ printf "KV/1.0 PUT city Hanoi\nKV/1.0 GET city\nKV/1.0 STATS\nKV/1.0 QUIT\n" | nc -q1 127.0.0.1 5050
201 CREATED
200 OK Hanoi
200 OK keys=1 uptime=0s served=13
200 OK bye

$ telnet 127.0.0.1 5050
Trying 127.0.0.1...
Connected to 127.0.0.1.
Escape character is '^]'.
KV/1.0 PUT city Hanoi
201 CREATED
KV/1.0 GET city
200 OK Hanoi
KV/1.0 QUIT
200 OK bye
Connection closed by foreign host.
```

Trích `server.log` (ghi mọi request/response kèm timestamp):

```
[2026-09-22 15:48:36.258] 127.0.0.1:5050 -- KVSS server listening (pid=6692)
[2026-09-22 15:48:36.731] 127.0.0.1:43816 -- connected
[2026-09-22 15:48:37.036] 127.0.0.1:43816 C->S 'KV/1.0 PUT city Hanoi'
[2026-09-22 15:48:37.037] 127.0.0.1:43816 S->C '201 CREATED'
[2026-09-22 15:48:37.343] 127.0.0.1:43816 C->S 'KV/1.0 GET city'
[2026-09-22 15:48:37.343] 127.0.0.1:43816 S->C '200 OK Hanoi'
[2026-09-22 15:48:37.648] 127.0.0.1:43816 C->S 'KV/1.0 QUIT'
[2026-09-22 15:48:37.648] 127.0.0.1:43816 S->C '200 OK bye'
```

Ghi chú thú vị: khi mở `http://127.0.0.1:5050` bằng trình duyệt, server nhận được các dòng HTTP (`GET / HTTP/1.1`, `Host: …`) và trả `426 UPGRADE_REQUIRED` cho từng dòng vì không có tiền tố `KV/1.0` – minh họa server từ chối mọi client không tuân thủ Interface.

### 1.4. Quan sát bằng Wireshark

Do WSL2 là máy ảo riêng, Wireshark trên Windows không thấy loopback bên trong WSL. Cách làm: server bind `0.0.0.0:5050` trong WSL, client chạy từ Windows nối tới IP WSL (`172.21.64.196`), Wireshark bắt trên adapter **vEthernet (WSL)** với capture filter `tcp port 5050`. File: `kvss/capture/kvss_session.pcapng`.

```
 1  172.21.64.1 → 172.21.64.196  [SYN]                       Len=0     ┐
 2  172.21.64.196 → 172.21.64.1  [SYN, ACK]                  Len=0     │ bắt tay 3 bước
 3  172.21.64.1 → 172.21.64.196  [ACK]                       Len=0     ┘
 4  C → S  [PSH, ACK] Seq=1   Len=24   "KV/1.0 PUT user42 Alice\n"
 5  S → C  [ACK]                       (ACK thuần, do server xử lý xong mới trả lời)
 6  S → C  [PSH, ACK] Seq=1   Len=12   "201 CREATED\n"
 7  C → S  [PSH, ACK] Seq=25  Len=18   "KV/1.0 GET user42\n"
 8  S → C  [PSH, ACK] Seq=13  Len=13   "200 OK Alice\n"
 9  C → S  [PSH, ACK] Seq=43  Len=18   "KV/1.0 DEL user42\n"
10  S → C  [PSH, ACK] Seq=26  Len=15   "204 NO_CONTENT\n"
11  C → S  [PSH, ACK] Seq=61  Len=18   "KV/1.0 GET user42\n"
12  S → C  [PSH, ACK] Seq=41  Len=14   "404 NOT_FOUND\n"
13  C → S  [PSH, ACK] Seq=79  Len=12   "PUT nover x\n"
14  S → C  [PSH, ACK] Seq=55  Len=21   "426 UPGRADE_REQUIRED\n"
15  C → S  [PSH, ACK] Seq=91  Len=25   "KV/1.0 POTT user42 Alice\n"
16  S → C  [PSH, ACK] Seq=76  Len=16   "400 BAD_REQUEST\n"
17  C → S  [PSH, ACK] Seq=116 Len=13   "KV/1.0 STATS\n"
18  S → C  [PSH, ACK] Seq=92  Len=35   "200 OK keys=0 uptime=41s served=15\n"
19  C → S  [PSH, ACK] Seq=129 Len=12   "KV/1.0 QUIT\n"
20  S → C  [PSH, ACK] Seq=127 Len=11   "200 OK bye\n"
21  S → C  [FIN, ACK]                                                  ┐
22  C → S  [ACK]                                                       │ server chủ động đóng
23  C → S  [FIN, ACK]                                                  │ sau QUIT (4 bước)
24  S → C  [ACK]                                                       ┘
```

Follow TCP Stream (Analyze → Follow → TCP Stream) cho thấy toàn bộ hội thoại dạng văn bản, đỏ = client, xanh = server:

```
KV/1.0 PUT user42 Alice          201 CREATED
KV/1.0 GET user42                200 OK Alice
KV/1.0 DEL user42                204 NO_CONTENT
KV/1.0 GET user42                404 NOT_FOUND
PUT nover x                      426 UPGRADE_REQUIRED
KV/1.0 POTT user42 Alice         400 BAD_REQUEST
KV/1.0 STATS                     200 OK keys=0 uptime=41s served=15
KV/1.0 QUIT                      200 OK bye
```

*(Chèn ảnh chụp màn hình Wireshark: danh sách gói với filter `tcp.port == 5050`, và cửa sổ Follow TCP Stream.)*

### 1.5. Trả lời câu hỏi

**Câu 1. Interface trong hệ thống phân tán là gì? Tại sao cần Interface khi triển khai dịch vụ?**

Interface là *hợp đồng* (contract) được quy định trước giữa bên cung cấp dịch vụ (server) và bên sử dụng (client), gồm: cách kết nối (TCP host:port), định dạng thông điệp (dòng văn bản UTF-8 kết thúc `\n`), cú pháp lệnh (BNF: `KV/1.0 <CMD> [key [value]]`), ngữ nghĩa từng lệnh, tập mã trạng thái phản hồi và phiên bản giao thức. Interface chỉ mô tả *cái gì* được trao đổi, không mô tả *cách cài đặt* bên trong.

Cần Interface vì trong hệ phân tán các thành phần chạy trên máy khác nhau, viết bằng ngôn ngữ khác nhau, do người khác nhau phát triển, không chia sẻ bộ nhớ – cách duy nhất để chúng hợp tác là qua thông điệp, nên phải thống nhất trước "ngôn ngữ chung":
- **Tính thống nhất / tương thích (interoperability):** trong lab, server Python nhận request từ `client.py`, `nc`, `telnet` và cả client chạy trên Windows – tất cả đều hiểu nhau vì cùng tuân thủ KV/1.0.
- **Che giấu cài đặt (encapsulation):** client không cần biết server lưu bằng `dict`, dùng `select()` hay thread; server có thể đổi cài đặt mà client không đổi.
- **Kiểm thử và phát hiện lỗi rõ ràng:** mọi tình huống sai đều có mã lỗi định nghĩa trước (400/404/426…), không phải "mạnh ai nấy làm".
- **Tiến hóa / mở rộng:** trường phiên bản `KV/1.0` cho phép ra KV/2.0 mà vẫn nhận biết client cũ.

**Câu 2. Ý nghĩa của 201 CREATED, 204 NO_CONTENT, 404 NOT_FOUND trong KVSS.**

| Mã | Ý nghĩa trong KVSS | Khi nào |
|---|---|---|
| `201 CREATED` | Yêu cầu thành công **và** một tài nguyên mới (key) vừa được tạo. Phân biệt với `200 OK` là PUT ghi đè key đã có. | `PUT user42 Alice` lần đầu |
| `204 NO_CONTENT` | Yêu cầu thành công nhưng **không có dữ liệu** để trả về – xóa xong thì không có value nào để gửi. | `DEL user42` khi key tồn tại |
| `404 NOT_FOUND` | Cú pháp đúng, nhưng key được yêu cầu **không tồn tại** trong store. Đây là lỗi phía client (nhóm 4xx), không phải lỗi server. | `GET nokey`, `DEL` key đã xóa |

Các mã này mượn ngữ nghĩa của HTTP để ai đã quen HTTP đọc là hiểu ngay: 2xx = thành công, 4xx = lỗi từ client, 5xx = lỗi server. Nhờ đó client có thể phân nhánh xử lý theo mã mà không cần phân tích chuỗi mô tả.

**Câu 3. Nếu client thiếu version `KV/1.0`, server phản hồi thế nào? Tại sao phải quy định rõ?**

Server kiểm tra token đầu tiên của mỗi dòng; nếu khác `KV/1.0` (thiếu hoặc `KV/2.0`) thì trả `426 UPGRADE_REQUIRED` và **không** thực hiện lệnh (TC07, TC08). Kết nối vẫn giữ để client gửi lại đúng chuẩn.

Phải quy định rõ vì:
1. **Tránh hành vi không xác định:** nếu không quy định, mỗi server có thể xử lý khác nhau (bỏ qua, đoán, crash) → client không thể dựa vào.
2. **Hỗ trợ tiến hóa giao thức:** version là cơ chế để nhiều phiên bản cùng tồn tại. Mã 426 nói rõ "bạn phải nâng cấp/đổi phiên bản", khác với 400 "cú pháp sai" – client biết chính xác phải sửa gì.
3. **An toàn:** không thực hiện lệnh khi chưa chắc client hiểu đúng ngữ nghĩa của phiên bản này (ví dụ KV/2.0 có thể đổi ý nghĩa của DEL).
4. **Phát hiện sớm client "lạ":** ví dụ trình duyệt gửi `GET / HTTP/1.1` vào cổng 5050 lập tức nhận 426.

**Câu 4. Qua Wireshark, mô tả cách gói tin TCP được chia để truyền thông điệp theo line-based protocol.**

Quan sát file `kvss_session.pcapng` (mục 1.4):
- TCP là **luồng byte (byte stream)**, bản thân nó không biết "thông điệp" là gì. Ranh giới thông điệp do **tầng ứng dụng** định nghĩa bằng ký tự `\n`.
- Trong phiên bắt được, mỗi lần client gọi `send()` một dòng, TCP đóng thành **một segment** có cờ `PSH, ACK`, `Len` đúng bằng độ dài dòng kể cả `\n` (ví dụ `"KV/1.0 PUT user42 Alice\n"` = 24 byte → `Len=24`). Cờ PSH báo bên nhận đẩy ngay dữ liệu lên ứng dụng thay vì chờ đầy buffer.
- Số `Seq` tăng đúng bằng `Len` của segment trước: 1 → 25 → 43 → 61…, cho thấy các dòng nối tiếp nhau trong cùng một luồng byte.
- Phản hồi của server đi ngược lại cũng mỗi dòng một segment; ACK được ghép (piggyback) vào segment dữ liệu kế tiếp, chỉ gói #5 là ACK thuần vì server mất một chút thời gian xử lý trước khi gửi trả lời.
- Đầu phiên là bắt tay 3 bước (SYN, SYN-ACK, ACK), cuối phiên sau `QUIT` server chủ động gửi FIN – đóng 4 bước.
- **Quan trọng:** việc "1 dòng = 1 segment" chỉ là hệ quả của lab nhỏ (dòng ngắn, gửi cách quãng). TCP hoàn toàn có thể **gộp** nhiều dòng vào một segment (Nagle) hoặc **cắt** một dòng thành nhiều segment (dòng dài hơn MSS 1460, hoặc client gửi từng phần – TC12 mô phỏng chính trường hợp này). Vì vậy server phải buffer dữ liệu nhận được và chỉ xử lý khi thấy `\n`, không được giả định mỗi `recv()` = một thông điệp. Đó là lý do line-based protocol chọn `\n` làm dấu phân cách rõ ràng.

**Câu 5. Client gửi `KV/1.0 POTT user42 Alice`. Server xử lý thế nào? Thể hiện đặc điểm gì của Interface?**

Server: version `KV/1.0` đúng → kiểm tra command `POTT` không thuộc tập `{PUT, GET, DEL, STATS, QUIT}` → trả `400 BAD_REQUEST`, không thay đổi store, không đóng kết nối (TC10 và gói #15–16 trong Wireshark). Server **không đoán** rằng client "chắc muốn PUT".

Điều này thể hiện:
- **Interface là hợp đồng nghiêm ngặt (strict contract):** chỉ những gì được định nghĩa mới hợp lệ; server không được tự suy diễn ý định client, vì suy diễn sẽ dẫn đến hành vi không xác định và khác nhau giữa các cài đặt.
- **Tính đóng của tập lệnh (closed set of operations):** Interface liệt kê đầy đủ các thao tác; mở rộng phải qua phiên bản mới, không qua "lệnh gần giống".
- **Xử lý lỗi có định nghĩa (well-defined error handling):** kể cả input sai cũng nhận phản hồi chuẩn có mã lỗi, nên client vẫn hoạt động ổn định và biết cách sửa; server không crash (robustness).
- **Tách bạch lớp lỗi:** thiếu version → 426, lệnh sai → 400, key không có → 404 – mỗi loại vi phạm hợp đồng có mã riêng, giúp chẩn đoán chính xác.

---

## PHẦN 2 – KIẾN TRÚC MICROSERVICES TRÊN KUBERNETES

*(Đang thực hiện – sẽ bổ sung kết quả `kubectl get pods/svc/ingress`, `curl`, scale và câu hỏi 6–8.)*
