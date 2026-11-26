#!/bin/bash
# Câu 8: server ngủ 2s/request, 4 client chạy cùng lúc, theo dõi hàng đợi
cd "$(dirname "$0")"
CP=.:amqp-client-5.5.1.jar:slf4j-api-1.7.25.jar:slf4j-simple-1.7.25.jar
mkdir -p d && cp delay/RPCServer.java d/ && (cd d && javac -cp ../amqp-client-5.5.1.jar RPCServer.java) && echo "javac delay OK"
(cd d && setsid nohup java -cp .:../amqp-client-5.5.1.jar:../slf4j-api-1.7.25.jar:../slf4j-simple-1.7.25.jar RPCServer > ../server2.log 2>&1 < /dev/null &)
sleep 4
for i in 1 2 3 4; do (timeout 90 java -cp $CP RPCClient > client2_$i.log 2>&1 &); done
sleep 6
for k in 1 2 3; do
  echo "\$ rabbitmqctl list_queues name messages_ready messages_unacknowledged   (t=+$((6+(k-1)*5))s)"
  rabbitmqctl list_queues name messages_ready messages_unacknowledged 2>&1 | grep -v -E "Timeout|Listing"
  sleep 5
done
echo "--- consumers"; rabbitmqctl list_consumers 2>&1 | grep -v -E "Timeout|Listing" | head
sleep 10
echo "--- progress client logs (dòng cuối)"; for i in 1 2 3 4; do tail -1 client2_$i.log; done
pkill -f RPCClient; pkill -f RPCServer
