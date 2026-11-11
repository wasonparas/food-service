# Restaurant + Order EKS Demo

A small two-service application for demonstrating Kubernetes / Amazon EKS:
- **Restaurant Service**: returns a list of restaurants.
- **Order Service**: creates and lists orders; calls Restaurant Service to validate restaurant IDs.
- Each service is a Python Flask app with a Dockerfile.
- Kubernetes manifests include Deployments, ClusterIP Services, and an optional AWS Load Balancer Controller Ingress.

> Demo app only: in-memory data resets when pods restart. Do not use for production.

## Architecture

```text
Browser / curl
     |
 AWS ALB (optional; AWS Load Balancer Controller)
     |  /restaurants -> restaurant-service
     |  /orders      -> order-service
     v
 Kubernetes ClusterIP Services
     |                         |
 restaurant-service             order-service
     |                         |
 Restaurant Pods <------------- Order Pods
```

## Repository layout

```text
restaurant-order-eks-demo/
├── restaurant-service/
├── order-service/
└── kubernetes/
    ├── namespace.yaml
    ├── restaurant.yaml
    ├── order.yaml
    └── ingress.yaml
```

## 1. Build and push images

Set your ECR repository names and AWS account/region:

```bash
export AWS_REGION=ap-southeast-2
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

aws ecr create-repository --repository-name restaurant-service --region "$AWS_REGION" || true
aws ecr create-repository --repository-name order-service --region "$AWS_REGION" || true

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"


docker build -t restaurant-service:1.0 ./restaurant-service
docker build -t order-service:1.0 ./order-service

docker tag restaurant-service:1.0 "$ECR_REGISTRY/restaurant-service:1.0"
docker tag order-service:1.0 "$ECR_REGISTRY/order-service:1.0"

docker push "$ECR_REGISTRY/restaurant-service:1.0"
docker push "$ECR_REGISTRY/order-service:1.0"
```

## 2. Update image references

Edit `kubernetes/restaurant.yaml` and `kubernetes/order.yaml`, replacing:
- `ACCOUNT_ID` with your AWS account ID
- `REGION` with your AWS region

Or run:

```bash
sed -i "s/ACCOUNT_ID/${AWS_ACCOUNT_ID}/g; s/REGION/${AWS_REGION}/g" kubernetes/restaurant.yaml kubernetes/order.yaml
```

## 3. Deploy to EKS

```bash
aws eks update-kubeconfig --region ap-southeast-2 --name test-cluster


kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/restaurant.yaml
kubectl apply -f kubernetes/order.yaml

kubectl rollout status deployment/restaurant-service -n food-demo
kubectl rollout status deployment/order-service -n food-demo
kubectl get pods,svc -n food-demo
```

## 4. Test inside the cluster (no ALB required)

```bash
kubectl run curl-test -n food-demo --image=curlimages/curl:8.10.1 --rm -it --restart=Never -- \
  curl http://restaurant-service/restaurants
```

Create an order (replace restaurant ID if needed):

```bash
kubectl run curl-test -n food-demo --image=curlimages/curl:8.10.1 --rm -it --restart=Never -- \
  curl -X POST http://order-service/orders \
  -H 'Content-Type: application/json' \
  -d '{"restaurant_id":1,"item":"Chicken Burger","quantity":2}'
```

List orders:

```bash
kubectl run curl-test -n food-demo --image=curlimages/curl:8.10.1 --rm -it --restart=Never -- \
  curl http://order-service/orders
```

## 5. Optional: expose with AWS ALB

Prerequisites:
- AWS Load Balancer Controller installed and IAM permissions configured.
- An ALB-capable IngressClass (commonly `alb`).

```bash
kubectl apply -f kubernetes/ingress.yaml
kubectl get ingress -n food-demo -w
```

When the ALB address appears, test:

```bash
curl http://ALB-DNS/restaurants/restaurants
curl http://ALB-DNS/orders/orders
```

The Ingress routes `/restaurants` and `/orders` prefixes to the respective services. This demo keeps the application endpoints under those prefixes.


http://k8s-fooddemo-fooddemo-08301086d4-914044465.ap-southeast-2.elb.amazonaws.com/restaurants

http://k8s-fooddemo-fooddemo-08301086d4-914044465.ap-southeast-2.elb.amazonaws.com/orders

## 6. KT demo commands

```bash
# Observe resources
kubectl get all -n food-demo
kubectl describe deployment restaurant-service -n food-demo
kubectl logs deployment/order-service -n food-demo

# Scale out
kubectl scale deployment restaurant-service --replicas=3 -n food-demo
kubectl get pods -n food-demo -w

# Self-healing: delete one pod and watch replacement
kubectl delete pod -n food-demo -l app=restaurant-service
kubectl get pods -n food-demo -w

# Rollout / image update (after pushing tag 1.1)
kubectl set image deployment/restaurant-service restaurant-service="$ECR_REGISTRY/restaurant-service:1.1" -n food-demo
kubectl rollout status deployment/restaurant-service -n food-demo
kubectl rollout undo deployment/restaurant-service -n food-demo

# Clean up
kubectl delete namespace food-demo
```

## API summary

### Restaurant Service
- `GET /health`
- `GET /restaurants`
- `GET /restaurants/<id>`

### Order Service
- `GET /health`
- `POST /orders` JSON: `{"restaurant_id":1,"item":"Pizza","quantity":1}`
- `GET /orders`
- Order creation calls `http://restaurant-service/restaurants/<id>` internally.

## Troubleshooting

```bash
kubectl get pods -n food-demo
kubectl describe pod POD_NAME -n food-demo
kubectl logs deployment/restaurant-service -n food-demo
kubectl logs deployment/order-service -n food-demo
kubectl get events -n food-demo --sort-by=.lastTimestamp
```

If pods show `ImagePullBackOff`, check ECR image URI, tag, and node IAM permissions for ECR pull.
