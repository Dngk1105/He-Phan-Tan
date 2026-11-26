#!/usr/bin/env python3
"""Đo chất lượng luồng video dưới các điều kiện NetEm.
Cách dùng:  measure.py <nhan> <http|udp> "<tham số netem>" [số giây]
Mô hình: srv(10.0.0.1) --NetEm trên eth0 của srv--> cli(10.0.0.2); VLC phát ở srv, ffmpeg thu và giải mã ở cli.
"""
import subprocess, sys, os, re, time, json, signal, shutil, threading

label, proto, netem = sys.argv[1], sys.argv[2], sys.argv[3]
dur = int(sys.argv[4]) if len(sys.argv) > 4 else 20
OUT = "/root/results"; os.makedirs(OUT, exist_ok=True)
SHOTS = f"{OUT}/shots_{label}"; shutil.rmtree(SHOTS, ignore_errors=True); os.makedirs(SHOTS)


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def ns(n, cmd):
    return f"ip netns exec {n} {cmd}"


# 1. áp NetEm lên eth0 của srv
sh(ns("srv", "tc qdisc del dev eth0 root"))
if netem.strip():
    r = sh(ns("srv", f"tc qdisc add dev eth0 root netem {netem}"))
    if r.returncode:
        print("tc error", r.stderr); sys.exit(1)

# 2. ping srv -> cli
p = sh(ns("srv", "ping -c 10 -i 0.2 -W 3 10.0.0.2")).stdout
m = re.search(r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", p)
l = re.search(r"(\d+)% packet loss", p)
ping = dict(loss=int(l.group(1)) if l else None, min=float(m.group(1)) if m else None,
            avg=float(m.group(2)) if m else None, max=float(m.group(3)) if m else None,
            mdev=float(m.group(4)) if m else None)

# 3. iperf3 UDP 2 Mbit/s trong 8 giây (srv -> cli): jitter và tỷ lệ mất gói
srvp = subprocess.Popen(ns("cli", "iperf3 -s -1"), shell=True, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
time.sleep(1)
ip = sh(ns("srv", "iperf3 -c 10.0.0.2 -u -b 2M -l 1200 -t 8"), timeout=60).stdout
try:
    os.killpg(srvp.pid, signal.SIGKILL)
except Exception:
    pass
rm = re.search(r"([\d.]+) ms\s+(\d+)/(\d+) \(([\d.e+-]+)%\)\s+receiver", ip)
iperf = (dict(jitter_ms=float(rm.group(1)), lost=int(rm.group(2)), total=int(rm.group(3)),
              lost_pct=float(rm.group(4))) if rm else {})

# 4. luồng video
if proto == "http":
    sout = "#standard{access=http,mux=ogg,dst=10.0.0.1:8080}"
    src = "/root/vid/video.ogv"; url = "http://10.0.0.1:8080"
else:
    sout = "#standard{access=udp,mux=ts,dst=10.0.0.2:5004}"
    src = "/root/vid/video.ts"; url = "udp://10.0.0.2:5004?fifo_size=8000000&overrun_nonfatal=1"
log = f"{OUT}/ffmpeg_{label}.log"
PRE = os.environ.get("FFPRE", "")  # ví dụ "-fflags nobuffer -probesize 32 -analyzeduration 0" = tắt đệm phía client
ff = (f"ffmpeg -hide_banner -y -loglevel info -stats_period 0.2 {PRE} -i '{url}' "
      f"-map 0:v -f null - -map 0:v -vf fps=1/4 {SHOTS}/f_%02d.png")

stamps = []  # (thời điểm thực, số frame đã giải mã)


def reader(proc, fh):
    buf = b""
    while True:
        ch = proc.stderr.read(1)
        if not ch:
            break
        fh.write(ch); buf += ch
        if ch in (b"\r", b"\n"):
            mm = re.search(rb"frame=\s*(\d+)", buf)
            if mm:
                stamps.append((time.time(), int(mm.group(1))))
            buf = b""
    fh.flush()


vlc = None


def start_vlc():
    global vlc
    vlc = subprocess.Popen(ns("srv", f"runuser -u vlcuser -- cvlc -I dummy {src} --loop --sout '{sout}'"),
                           shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)


def run_client():
    c = subprocess.Popen(ns("cli", f"timeout {dur} {ff}"), shell=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.PIPE, preexec_fn=os.setsid)
    rt = threading.Thread(target=reader, args=(c, open(log, "wb")))
    rt.start()
    return c, rt


if proto == "http":
    start_vlc(); time.sleep(2.5)
    t0 = time.time(); c, rt = run_client()
else:
    c, rt = run_client(); time.sleep(1)
    t0 = time.time(); start_vlc()
c.wait(); rt.join()
try:
    os.killpg(vlc.pid, signal.SIGKILL)
except Exception:
    pass
sh("pkill -u vlcuser vlc")
sh(ns("srv", "tc qdisc del dev eth0 root"))

# 5. phân tích
txt = open(log, errors="ignore").read()
pats = {"corrupt": "corrupt", "continuity": "Continuity check failed", "invalid": "invalid",
        "decode_err": "Error while decoding|decode error|error while", "conceal": "concealing|missing reference",
        "ts_err": "PTS|DTS|non monotonic|out of order"}
errs = {k: len(re.findall(v, txt, re.I)) for k, v in pats.items()}

first = None; stall = 0.0; longest = 0.0; nstalls = 0
last_t = None; last_f = 0; run_gap = 0.0
for t, f in stamps:
    if f > 0 and first is None:
        first = round(t - t0, 1)
    if first is not None:
        if f > last_f:
            if run_gap > 0.5:
                nstalls += 1
            run_gap = 0.0
        elif last_t is not None:
            run_gap += t - last_t
            longest = max(longest, run_gap)
            stall += t - last_t
    last_t, last_f = t, f
nf = stamps[-1][1] if stamps else 0
res = dict(label=label, proto=proto, netem=netem, ping=ping, iperf=iperf, frames=nf, first_frame_s=first,
           stall_s=round(stall, 1), longest_stall_s=round(longest, 1), n_stalls=nstalls, errors=errs,
           shots=len(os.listdir(SHOTS)))
print(json.dumps(res, ensure_ascii=False))
open(f"{OUT}/results.jsonl", "a").write(json.dumps(res, ensure_ascii=False) + "\n")
