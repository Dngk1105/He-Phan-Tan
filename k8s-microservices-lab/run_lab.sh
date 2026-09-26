#!/usr/bin/env bash
# Chạy lại toàn bộ Phần 2 (microservices trên Kubernetes) và in ra giống phiên terminal.
# Cách dùng:  bash run_lab.sh | tee lab_session.log
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")"
PROMPT="dunght2408@DUNG:~/Hệ Phân Tán/Chap1/k8s-microservices-lab\$"

run() { echo "$PROMPT $*"; eval "$@"; }

# Ingress controller chỉ route được từ trong mạng docker-desktop; dùng port-forward
# để gọi http://micro.local từ Ubuntu mà không cần sudo.
summary='python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({\"service\": d[\"environment\"][\"CUSTOM_RESPONSE__SERVICE\"], \"hostname\": d[\"environment\"][\"HOSTNAME\"], \"originalUrl\": d[\"http\"][\"originalUrl\"]}))"'

# dọn trạng thái cũ (không in ra log)
kubectl delete namespace micro-lab --ignore-not-found --wait=true >/dev/null 2>&1

run kubectl get nodes
run kubectl create namespace micro-lab
run kubectl config set-context --current --namespace=micro-lab
run kubectl apply -f users-deploy.yaml
run kubectl apply -f catalog-deploy.yaml
run kubectl apply -f orders-deploy.yaml
run kubectl apply -f gateway-ingress.yaml
run kubectl rollout status deploy/users-deploy --timeout=120s
kubectl wait --for=condition=available --timeout=120s deploy --all >/dev/null
run kubectl get pods -l app=users
run kubectl get pods
run kubectl get svc
sleep 20   # chờ ingress-nginx gán ADDRESS
run kubectl get ingress
run minikube ip

run "kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80 >/dev/null 2>&1 &"
PF=$!
sleep 3
for p in users catalog orders; do
  run "curl -s --resolve micro.local:8080:127.0.0.1 http://micro.local:8080/$p | $summary"
done

run kubectl scale deploy catalog-deploy --replicas=3
run kubectl rollout status deploy/catalog-deploy --timeout=120s
sleep 8    # chờ ingress-nginx cập nhật upstream
run kubectl get pods -l app=catalog -o wide
run 'for i in $(seq 1 9); do curl -s --resolve micro.local:8080:127.0.0.1 http://micro.local:8080/catalog | grep -o "\"HOSTNAME\":\"[^\"]*\""; done'
kill $PF 2>/dev/null

run kubectl delete -f gateway-ingress.yaml
run kubectl delete -f users-deploy.yaml
run kubectl delete -f catalog-deploy.yaml
run kubectl delete -f orders-deploy.yaml
run kubectl delete namespace micro-lab
run kubectl config set-context --current --namespace=default
echo "$PROMPT"
