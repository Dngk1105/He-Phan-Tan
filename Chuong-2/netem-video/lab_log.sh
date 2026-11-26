#!/bin/bash
# Chạy lần lượt các lệnh của đề (Câu 9-17) và ghi lại nhật ký; mỗi bước đo thêm bằng chính VLC client.
cd "$(dirname "$0")"
bash setup.sh > /dev/null
V=/root/vid/video.ogv
S="ip netns exec srv"; C="ip netns exec cli"
LOG=/root/results/vlc_client; mkdir -p $LOG

vlc_server() {   # $1 = file, $2 = sout
  $S runuser -u vlcuser -- cvlc -I dummy -vvv "$1" --loop --sout "$2" > $LOG/server.log 2>&1 &
  sleep 2
}
vlc_probe() {    # $1 = nhãn, phần còn lại = tuỳ chọn thêm cho client (vd: --network-caching=0)
  local name=$1; shift
  pkill -u vlcuser vlc; sleep 1; vlc_server $V '#standard{access=http,mux=ogg,dst=10.0.0.1:8080}'   # khởi động lại server để mỗi lần đo bắt đầu từ đầu video
  $C timeout 25 runuser -u vlcuser -- cvlc -I dummy --vout dummy --aout dummy -vv --run-time=12 --play-and-exit "$@" http://10.0.0.1:8080 > $LOG/$name.log 2>&1
  local buf=$(grep -m1 -o "Stream buffering done ([0-9]* ms in [0-9]* ms)" $LOG/$name.log)
  local aud=$(grep -c "buffer too late" $LOG/$name.log)
  local vid=$(grep -c "picture is too late to be displayed" $LOG/$name.log)
  echo "   [VLC client $name] $buf ; audio bị bỏ (buffer too late)=$aud ; ảnh quá trễ=$vid"
}
stop_vlc() { pkill -u vlcuser vlc; sleep 1; }
step() { echo; echo "\$ $*"; }
q() { echo "\$ $*"; "$@"; }

echo "=== Câu 9: địa chỉ IP và ping ==="
echo "\$ ip addr   # máy Server (netns srv)";  $S ip -br -4 a show eth0
echo "\$ ip addr   # máy Client (netns cli)";  $C ip -br -4 a show eth0
echo "\$ ping -c 4 10.0.0.2   # từ Server"; $S ping -c 4 10.0.0.2
echo "\$ ping -c 4 10.0.0.1   # từ Client"; $C ping -c 4 10.0.0.1

echo; echo "=== Câu 10: phát video bằng VLC (HTTP, mux ogg) ==="
echo "\$ vlc -vvv video.ogv --sout '#standard{access=http,mux=ogg,dst=10.0.0.1:8080}'"
vlc_server $V '#standard{access=http,mux=ogg,dst=10.0.0.1:8080}'
grep -i -E "access_output_http|stream_out_standard|mux.*ogg|listening|http" $LOG/server.log | head -6 | cut -c1-140
echo "\$ vlc http://10.0.0.1:8080"
vlc_probe base
grep -i -E "decoder.*(theora|vorbis)|using .* decoder|codec .* (found|selected)|dummy|buffering" $LOG/base.log | head -8 | cut -c1-140

echo; echo "=== Câu 11: delay 100ms ==="
step "sudo tc qdisc add dev eth0 root netem delay 100ms"; $S tc qdisc add dev eth0 root netem delay 100ms
$S tc qdisc show dev eth0
echo "\$ ping -c 6 10.0.0.2   # Server -> Client"; $S ping -c 6 10.0.0.2

echo; echo "=== Câu 12: delay 100ms, client có và không có đệm ==="
vlc_probe delay100_buf
vlc_probe delay100_nobuf --network-caching=0 --live-caching=0

echo; echo "=== Câu 13: biến đổi độ trễ ==="
step "sudo tc qdisc change dev eth0 root netem delay 100ms 10ms"; $S tc qdisc change dev eth0 root netem delay 100ms 10ms
$S ping -c 6 10.0.0.2 | tail -3; vlc_probe delay_j10
step "sudo tc qdisc change dev eth0 root netem delay 100ms 10ms 25%"; $S tc qdisc change dev eth0 root netem delay 100ms 10ms 25%
$S ping -c 6 10.0.0.2 | tail -3; vlc_probe delay_j10_c25

echo; echo "=== Câu 14: mất gói ==="
step "sudo tc qdisc change dev eth0 root netem loss 0.1%"; $S tc qdisc change dev eth0 root netem loss 0.1%; vlc_probe loss01
step "sudo tc qdisc change dev eth0 root netem loss 5%"; $S tc qdisc change dev eth0 root netem loss 5%; vlc_probe loss5
echo; echo "=== Câu 15: mất gói có tương quan ==="
step "sudo tc qdisc change dev eth0 root netem loss 0.3% 25%"; $S tc qdisc change dev eth0 root netem loss 0.3% 25%; vlc_probe loss03_c25
step "sudo tc qdisc change dev eth0 root netem loss 5% 25%"; $S tc qdisc change dev eth0 root netem loss 5% 25%; vlc_probe loss5_c25

echo; echo "=== Câu 16: lặp gói ==="
step "sudo tc qdisc change dev eth0 root netem duplicate 1%"; $S tc qdisc change dev eth0 root netem duplicate 1%; vlc_probe dup1
step "sudo tc qdisc change dev eth0 root netem duplicate 20%"; $S tc qdisc change dev eth0 root netem duplicate 20%; vlc_probe dup20

echo; echo "=== Lỗi gói tin ==="
step "sudo tc qdisc change dev eth0 root netem corrupt 0.1%"; $S tc qdisc change dev eth0 root netem corrupt 0.1%; vlc_probe corrupt01
step "sudo tc qdisc change dev eth0 root netem corrupt 5%"; $S tc qdisc change dev eth0 root netem corrupt 5%; vlc_probe corrupt5

echo; echo "=== Câu 17: đảo thứ tự gói ==="
step "sudo tc qdisc change dev eth0 root netem delay 10ms reorder 100% gap 5"; $S tc qdisc change dev eth0 root netem delay 10ms reorder 100% gap 5; vlc_probe gap5
step "sudo tc qdisc change dev eth0 root netem delay 10ms reorder 25% 50%"; $S tc qdisc change dev eth0 root netem delay 10ms reorder 25% 50%; vlc_probe reorder25

echo; step "sudo tc qdisc del dev eth0 root"; $S tc qdisc del dev eth0 root; $S tc qdisc show dev eth0
stop_vlc
echo LABDONE
