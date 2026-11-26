# RabbitMQ RPC (Java)

Cần RabbitMQ chạy ở localhost. Tải các jar vào thư mục này:
- [amqp-client-5.5.1.jar](https://repo1.maven.org/maven2/com/rabbitmq/amqp-client/5.5.1/amqp-client-5.5.1.jar)
- [slf4j-api-1.7.25.jar](https://repo1.maven.org/maven2/org/slf4j/slf4j-api/1.7.25/slf4j-api-1.7.25.jar)
- [slf4j-simple-1.7.25.jar](https://repo1.maven.org/maven2/org/slf4j/slf4j-simple/1.7.25/slf4j-simple-1.7.25.jar)

```bash
CP=.:amqp-client-5.5.1.jar:slf4j-api-1.7.25.jar:slf4j-simple-1.7.25.jar
javac -cp $CP *.java
java -cp $CP RPCServer &
java -cp $CP RPCClient
```
- `part2_basic.sh`, `part2_delay.sh`: kịch bản thí nghiệm (dùng server trong `delay/` cho bản có độ trễ)
- `logs/`: log kết quả
