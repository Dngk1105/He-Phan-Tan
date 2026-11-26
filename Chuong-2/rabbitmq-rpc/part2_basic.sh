#!/bin/bash
cd "$(dirname "$0")"
CP=.:amqp-client-5.5.1.jar:slf4j-api-1.7.25.jar:slf4j-simple-1.7.25.jar
setsid nohup java -cp $CP RPCServer > server1.log 2>&1 < /dev/null &
sleep 4
timeout 60 java -cp $CP RPCClient > client1.log 2>&1
echo exit=$?
echo "--- client"; cat client1.log
echo "--- server"; cat server1.log
pkill -f RPCServer
