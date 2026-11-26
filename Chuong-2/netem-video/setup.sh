#!/bin/bash
# Dựng testbed 2 máy ảo bằng network namespace: srv (10.0.0.1) <-> cli (10.0.0.2), NetEm đặt trên giao diện eth0 của srv
set -e
ip netns del srv 2>/dev/null || true
ip netns del cli 2>/dev/null || true
ip netns add srv; ip netns add cli
ip link add vsrv type veth peer name vcli
ip link set vsrv netns srv name eth0
ip link set vcli netns cli name eth0
ip -n srv addr add 10.0.0.1/24 dev eth0; ip -n cli addr add 10.0.0.2/24 dev eth0
for n in srv cli; do ip -n $n link set lo up; ip -n $n link set eth0 up; done
modprobe sch_netem 2>/dev/null || true
echo "srv: $(ip -n srv -br a show eth0)"; echo "cli: $(ip -n cli -br a show eth0)"
