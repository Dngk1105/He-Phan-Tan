#!/usr/bin/env bash
# Chạy lại toàn bộ Phần 1 (KVSS) và in ra giống phiên terminal.
# Cách dùng:  bash run_lab.sh | tee lab_session.log
cd "$(dirname "$0")"
PROMPT="dunght2408@DUNG:~/Hệ Phân Tán/Chap1/kvss\$"
run() { echo "$PROMPT $*"; eval "$@"; }

pkill -f "server.py --port 5050" 2>/dev/null; sleep 0.3
rm -f server.log

run "python3 server.py --port 5050 --log server.log > /dev/null &"
sleep 0.5
run 'printf "PUT user42 Alice\nGET user42\nDEL user42\nGET user42\nSTATS\nQUIT\n" | python3 client.py'
run 'printf "PUT user42 Alice\nKV/1.0 PUT user42\nKV/1.0 POTT user42 Alice\nKV/1.0 DEL ghost\nKV/1.0 DEL ghost\nKV/1.0 QUIT\n" | python3 client.py --raw'
run 'printf "KV/1.0 PUT city Hanoi\nKV/1.0 GET city\nKV/1.0 STATS\nKV/1.0 QUIT\n" | nc -q1 127.0.0.1 5050'
run '{ sleep 0.3; printf "KV/1.0 GET city\r\n"; sleep 0.3; printf "KV/1.0 QUIT\r\n"; sleep 0.3; } | telnet 127.0.0.1 5050'
run python3 test_kvss.py
run cat server.log
pkill -f "server.py --port 5050" 2>/dev/null
echo "$PROMPT"
