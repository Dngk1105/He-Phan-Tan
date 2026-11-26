#!/bin/bash
# Câu 12 (bổ sung): so sánh client tắt đệm khi KHÔNG có delay và khi có delay 100ms
cd "$(dirname "$0")"; bash setup.sh >/dev/null
S="ip netns exec srv"; C="ip netns exec cli"; L=/root/results/vlc_client
probe() {  # $1 nhãn, $2 netem ("" = không có)
  pkill -u vlcuser vlc; sleep 1
  $S tc qdisc del dev eth0 root 2>/dev/null; [ -n "$2" ] && $S tc qdisc add dev eth0 root netem $2
  $S runuser -u vlcuser -- cvlc -I dummy /root/vid/video.ogv --loop --sout '#standard{access=http,mux=ogg,dst=10.0.0.1:8080}' > /dev/null 2>&1 &
  sleep 2
  $C timeout 25 runuser -u vlcuser -- cvlc -I dummy --vout dummy --aout dummy -vv --run-time=12 --play-and-exit --network-caching=0 --live-caching=0 http://10.0.0.1:8080 > $L/$1.log 2>&1
  echo "[VLC client $1, network-caching=0] $(grep -m1 -o 'Stream buffering done ([0-9]* ms in [0-9]* ms)' $L/$1.log) ; audio bị bỏ=$(grep -c 'buffer too late' $L/$1.log) ; ảnh quá trễ=$(grep -c 'picture is too late to be displayed' $L/$1.log)"
}
probe nobuf_nodelay ""
probe nobuf_delay100 "delay 100ms"
$S tc qdisc del dev eth0 root; pkill -u vlcuser vlc
