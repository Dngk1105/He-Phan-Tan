#!/bin/bash
# Chạy toàn bộ ma trận thử nghiệm (mất ~20 phút). Kết quả: /root/results/results.jsonl
cd "$(dirname "$0")"
bash setup.sh > /dev/null
rm -rf /root/results
D=18
run() { python3 measure.py "$1" "$2" "$3" $D; }
declare -a C=(
 "base|"
 "delay100|delay 100ms"
 "delay100_j10|delay 100ms 10ms"
 "delay100_j10_c25|delay 100ms 10ms 25%"
 "delay100_j50|delay 100ms 50ms 25%"
 "loss01|loss 0.1%"
 "loss5|loss 5%"
 "loss03_c25|loss 0.3% 25%"
 "loss5_c25|loss 5% 25%"
 "dup1|duplicate 1%"
 "dup20|duplicate 20%"
 "corrupt01|corrupt 0.1%"
 "corrupt5|corrupt 5%"
 "gap5|delay 10ms reorder 100% gap 5"
 "reorder25|delay 10ms reorder 25% 50%"
 "reorder50|delay 50ms reorder 50% 50%"
)
for e in "${C[@]}"; do
  n="${e%%|*}"; a="${e#*|}"
  run "udp_$n" udp "$a"
  run "http_$n" http "$a"
done
# Câu 12: client tắt bộ đệm, delay 100ms
FFPRE="-fflags nobuffer -probesize 32 -analyzeduration 0" python3 measure.py "http_nobuf_delay100" http "delay 100ms" $D
FFPRE="-fflags nobuffer -probesize 32 -analyzeduration 0" python3 measure.py "http_nobuf_base" http "" $D
echo ALLDONE
