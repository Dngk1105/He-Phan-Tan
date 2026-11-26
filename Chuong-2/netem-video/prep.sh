#!/bin/bash
# Tạo video thử nghiệm (thay cho video tải từ open-video.org vì máy lab không có Internet ổn định / tránh phụ thuộc)
mkdir -p /root/vid && cd /root/vid
id vlcuser >/dev/null 2>&1 || useradd -m vlcuser
ffmpeg -y -loglevel error -f lavfi -i testsrc2=size=640x360:rate=25 -f lavfi -i sine=frequency=440:sample_rate=44100 -t 60 \
  -c:v libtheora -q:v 7 -c:a libvorbis -b:a 96k video.ogv
ffmpeg -y -loglevel error -f lavfi -i testsrc2=size=640x360:rate=25 -f lavfi -i sine=frequency=440:sample_rate=44100 -t 60 \
  -c:v mpeg2video -b:v 1500k -c:a mp2 -b:a 96k -f mpegts video.ts
chmod -R a+rX /root /root/vid 2>/dev/null; chmod 755 /root
ls -l /root/vid; ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate -of compact video.ogv
