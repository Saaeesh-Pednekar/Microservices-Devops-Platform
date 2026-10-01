# 🚀 DevOps Platform — Automated CI/CD Pipeline

**A production-grade CI/CD pipeline demonstrating Django + React deployed to AWS EKS via Jenkins.**

[![Jenkins](https://img.shields.io/badge/Jenkins-CI%2FCD-D24939?logo=jenkins&logoColor=white)](https://www.jenkins.io/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-EKS-326CE5?logo=kubernetes&logoColor=white)](https://aws.amazon.com/eks/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-ECR%20%7C%20EKS-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/)

---

## 📖 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Part 1 — Application & Containerization](#part-1--application--containerization)
5. [Part 2 — Infrastructure Setup (AWS)](#part-2--infrastructure-setup-aws)
6. [Part 3 — Kubernetes Manifests](#part-3--kubernetes-manifests)
7. [Part 4 — Automated CI/CD (Jenkinsfile)](#part-4--automated-cicd-jenkinsfile)
8. [Part 5 — Running the Full Pipeline](#part-5--running-the-full-pipeline)
<!-- 9. [Part 6 — Interview Talking Points](#part-6--interview-talking-points)
10. [Cleanup](#cleanup) -->

---

## Architecture Overview

```text
Developer
   │
   │  git push
   ▼
GitHub Repository
   │
   │  webhook
   ▼
Jenkins CI/CD Pipeline
   ├─ Checkout source code
   ├─ Run Django tests + frontend lint
   ├─ Build backend/frontend images
   ├─ Push images to Amazon ECR
   └─ Deploy manifests to Amazon EKS
            │
            ▼
       Amazon ECR
            │
            ▼
       Amazon EKS Cluster
            │
            ▼
     ┌───────────────────────────────┐
     │   nginx Ingress Controller   │
     │   (creates public ALB)        │
     └──────────────┬────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Frontend Service     │
         │ Type: ClusterIP      │
         └──────────┬───────────┘
                    │
                    ▼
          Frontend Nginx Proxy
                    │
                    │ /api/* requests
                    ▼
         ┌──────────────────────┐
         │ Backend Service      │
         │ Type: ClusterIP      │
         └──────────┬───────────┘
                    │
                    ▼
             Django REST API
                    │
                    ▼
               Public Internet
```

1. Developer pushes code to GitHub
2. GitHub webhook triggers Jenkins pipeline
3. Jenkins runs lint/tests, builds Docker images, and pushes them to ECR
4. Jenkins updates Kubernetes deployments on EKS
5. The public entrypoint is the nginx ingress controller, which creates an AWS load balancer
6. The ingress forwards traffic to the frontend `ClusterIP` service, and the frontend Nginx proxy sends API calls to the backend service over the cluster network

---

## Project Structure

```
Devops_platform/
├── backend/                    # Django REST API
│   ├── api/
│   │   ├── __init__.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── Dockerfile              # Multi-stage, non-root, optimized
│   ├── .dockerignore
│   ├── manage.py
│   └── requirements.txt
├── frontend/                   # React + Vite SPA
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── Dockerfile              # Multi-stage build with Nginx
│   ├── .dockerignore
│   ├── nginx.conf
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml
│   ├── django-secret.yaml
│   ├── backend-deployment.yaml
│   ├── backend-hpa.yaml
│   ├── backend-service.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-hpa.yaml
│   ├── frontend-service.yaml    # Internal ClusterIP service for ingress routing
│   ├── ingress.yaml             # nginx ingress route to the frontend service
│   ├── jenkins-values.yaml      # Jenkins Helm values for EKS
│   ├── jenkins-agent-rbac.yaml  # Controller permissions for agents
│   └── jenkins-deployer-rbac.yaml # Deployment permissions for Jenkins
├── Jenkinsfile                 # Declarative CI/CD pipeline
├── .gitignore
└── README.md                   # ← You are here
```

---

## Prerequisites

Install these tools on your local machine before starting:

| Tool                                                                              | Version   | Purpose                        |
| --------------------------------------------------------------------------------- | --------- | ------------------------------ |
| [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) | ≥ 2.x     | Interact with AWS services     |
| [eksctl](https://eksctl.io/installation/)                                         | ≥ 0.190.0 | Create and manage EKS clusters |
| [kubectl](https://kubernetes.io/docs/tasks/tools/)                                | ≥ 1.28    | Manage Kubernetes resources    |
| [Docker](https://docs.docker.com/get-docker/)                                     | ≥ 24.x    | Build container images         |
| [Node.js](https://nodejs.org/)                                                    | ≥ 20.x    | Build frontend                 |
| [Python](https://www.python.org/)                                                 | ≥ 3.12    | Run backend                    |
| [Git](https://git-scm.com/)                                                       | ≥ 2.x     | Version control                |

**Verify installations:**

```bash
aws --version
eksctl version
kubectl version --client
docker --version
node --version
python3 --version
git --version
```

---

## Part 1 — Application & Containerization

### 1.1 The Application

This project is a full-stack **Task Manager** with two services:

#### Backend (Django REST API)

| Endpoint                  | Method | Description                                |
| ------------------------- | ------ | ------------------------------------------ |
| `/api/health/`            | GET    | Health check for K8s probes                |
| `/api/info/`              | GET    | App version, hostname, environment, uptime |
| `/api/tasks/`             | GET    | List all tasks                             |
| `/api/tasks/add/`         | POST   | Create a new task                          |
| `/api/tasks/toggle/<id>/` | PATCH  | Toggle task completion                     |
| `/api/tasks/delete/<id>/` | DELETE | Delete a task                              |

The `/api/info/` endpoint returns real-time metadata that changes per pod — this is how you can visually confirm rolling updates and multi-pod deployments:

```json
{
  "app_name": "DevOps Platform",
  "version": "a3f7c2d",
  "environment": "production",
  "hostname": "backend-7b8c9d4f5-x2kl9",
  "python_version": "3.12.6",
  "uptime": "2h 15m 30s",
  "timestamp": "2026-09-18T09:30:00+00:00"
}
```

#### Frontend (React + Vite)

A sleek dark-themed dashboard that:

- Displays live app metadata (version, hostname, uptime, environment)
- Provides a task manager (add, toggle, delete tasks)
- Auto-refreshes data every 30 seconds
- Uses Nginx as a production web server with API reverse-proxy

### 1.2 Multi-Stage Dockerfiles

Both services use **optimized multi-stage builds** with security best practices:

#### Backend Dockerfile (`backend/Dockerfile`)

**Key optimizations:**

- **Multi-stage build**: The `builder` stage installs dependencies into a virtual environment; the `production` stage copies only the venv — keeping the final image < 200MB
- **Non-root user**: Runs as `appuser` (not root) to reduce the attack surface
- **No build tools in production**: `gcc` and `libpq-dev` stay in the discarded builder stage
- **HEALTHCHECK**: Built-in Docker health check hitting `/api/health/`
- **Gunicorn**: Production-grade WSGI server with 3 workers

#### Frontend Dockerfile (`frontend/Dockerfile`)

**Key optimizations:**

- **Multi-stage build**: Node.js compiles the React app; only the static `dist/` folder is copied to a tiny Nginx Alpine image (~25MB)
- **Non-root user**: Runs as the `nginx` user
- **Custom Nginx config**: Includes SPA routing fallback, API reverse-proxy to the backend service, security headers, and static asset caching

### 1.3 Build & Test Locally

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py test --verbosity=2
python manage.py runserver      # http://localhost:8000

# Frontend (in a new terminal)
cd frontend
npm install
npm run dev                     # http://localhost:3000
```

### 1.4 Build Docker Images Locally

```bash
# From the project root
docker build -t devops-backend  ./backend
docker build -t devops-frontend ./frontend

# Run locally
docker network create devops-net

docker run -d --name backend \
  --network devops-net \
  -p 8000:8000 \
  -e APP_ENVIRONMENT=local-docker \
  devops-backend

docker run -d --name frontend \
  --network devops-net \
  -p 3000:80 \
  devops-frontend

# Open http://localhost:3000
```

### 1.5 Run the full stack with Docker Compose

The Compose setup includes a local PostgreSQL 16 container. The backend uses PostgreSQL when `DB_HOST` is set and falls back to SQLite for non-Docker development.

```bash
# From the project root
docker compose up --build

# Apply migrations from another terminal when needed
docker compose exec backend-service python manage.py migrate

# Stop the services but keep PostgreSQL data
docker compose down

# Remove the local PostgreSQL data volume too
docker compose down -v
```

The local PostgreSQL connection uses database `devops_db`, user `devops_user`, and password `devops_password`. These values are intended for local testing only.

---

## Part 2 — Infrastructure Setup (AWS)

### 2.1 Configure AWS CLI

```bash
aws configure
# AWS Access Key ID:     <your-key>
# AWS Secret Access Key: <your-secret>
# Default region name:   us-east-1
# Default output format: json

# Verify
aws sts get-caller-identity
```

### 2.2 Create Amazon ECR Repositories

ECR (Elastic Container Registry) stores your Docker images. Create one repo per service:

```bash
# Create backend ECR repository
aws ecr create-repository \
    --repository-name devops-platform-backend \
    --region us-east-1 \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256

# Create frontend ECR repository
aws ecr create-repository \
    --repository-name devops-platform-frontend \
    --region us-east-1 \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256
```

**Note the output** — it contains your `repositoryUri` which looks like:

```
123456789012.dkr.ecr.us-east-1.amazonaws.com/devops-platform-backend
```

The `123456789012` is your AWS Account ID. You'll need this for the Jenkinsfile.

**Set a lifecycle policy** to auto-delete old images and save costs:

```bash
aws ecr put-lifecycle-policy \
    --repository-name devops-platform-backend \
    --region us-east-1 \
    --lifecycle-policy-text '{
        "rules": [
            {
                "rulePriority": 1,
                "description": "Keep only last 10 images",
                "selection": {
                    "tagStatus": "any",
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    }'

aws ecr put-lifecycle-policy \
    --repository-name devops-platform-frontend \
    --region us-east-1 \
    --lifecycle-policy-text '{
        "rules": [
            {
                "rulePriority": 1,
                "description": "Keep only last 10 images",
                "selection": {
                    "tagStatus": "any",
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    }'
```

### 2.3 Create the EKS Cluster

This command creates a fully managed 2-node Kubernetes cluster:

```bash
eksctl create cluster \
    --name devops-platform-cluster \
    --region us-east-1 \
    --version 1.31 \
    --nodegroup-name standard-workers \
    --node-type t3.medium \
    --nodes 2 \
    --nodes-min 1 \
    --nodes-max 3 \
    --managed \
    --with-oidc \
    --ssh-access \
    --ssh-public-key ~/.ssh/id_rsa.pub \
    --asg-access \
    --full-ecr-access
```

> ⏱️ **This takes 15-20 minutes.** `eksctl` creates a CloudFormation stack with the VPC, subnets, security groups, IAM roles, and the EKS control plane + managed node group.

**Flags explained:**

| Flag                          | Purpose                                       |
| ----------------------------- | --------------------------------------------- |
| `--version 1.31`              | Kubernetes version                            |
| `--node-type t3.medium`       | 2 vCPU, 4GB RAM — good for dev/demo           |
| `--nodes 2`                   | 2 worker nodes                                |
| `--nodes-min 1 --nodes-max 3` | Autoscaling range                             |
| `--managed`                   | AWS-managed node group (auto-patched)         |
| `--with-oidc`                 | Enables IRSA (IAM Roles for Service Accounts) |
| `--full-ecr-access`           | Nodes can pull images from ECR                |

**Verify the cluster:**

```bash
# Update kubeconfig
aws eks update-kubeconfig --name devops-platform-cluster --region us-east-1

# Verify
kubectl get nodes
# NAME                             STATUS   ROLES    AGE   VERSION
# ip-192-168-xx-xx.ec2.internal    Ready    <none>   5m    v1.31.x
# ip-192-168-yy-yy.ec2.internal    Ready    <none>   5m    v1.31.x

kubectl cluster-info
```

### 2.4 IAM Roles & Permissions (No Hardcoded Keys!)

> **⚠️ CRITICAL SECURITY PRINCIPLE**: Never store AWS Access Keys on Jenkins. Use **IAM Instance Profiles** instead.

#### How IAM Instance Profiles Work

```
┌────────────────────────────────────────────────────┐
│                AWS Account                         │
│                                                    │
│  ┌──────────────────┐    ┌─────────────────────┐   │
│  │  IAM Role:       │    │  IAM Role:          │   │
│  │  JenkinsEC2Role  │    │  EKS Node Role      │   │
│  │                  │    │  (auto by eksctl)   │   │
│  │  Policies:       │    │                     │   │
│  │  • ECR Push/Pull │    │  Policies:          │   │
│  │  • EKS Describe  │    │  • ECR Pull         │   │
│  │  • STS Assume    │    │  • EC2              │   │
│  └───────┬──────────┘    │  • CNI              │   │
│          │               └─────────────────────┘   │
│          │ attached via                            │
│          │ Instance Profile                        │
│          ▼                                         │
│  ┌──────────────────┐    ┌─────────────────────┐   │
│  │  EC2 Instance    │    │  EKS Cluster        │   │
│  │  (Jenkins)       │───▶│  devops-platform-  │   │
│  │                  │    │  cluster            │   │
│  │  No AWS keys     │    │                     │   │
│  │  stored here!    │    │  Worker nodes auto- │   │
│  └──────────────────┘    │  pull from ECR      │   │
│                          └─────────────────────┘   │
└────────────────────────────────────────────────────┘
```

#### Step-by-Step IAM Setup

**Step 1: Create the IAM Policy**

Create a file called `jenkins-iam-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAuthAndPush",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeRepositories",
        "ecr:ListImages"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EKSAccess",
      "Effect": "Allow",
      "Action": ["eks:DescribeCluster", "eks:ListClusters"],
      "Resource": "arn:aws:eks:us-east-1:*:cluster/devops-platform-cluster"
    },
    {
      "Sid": "STSGetCallerIdentity",
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
```

**Step 2: Create the IAM Role and Instance Profile**

```bash
# Create the IAM policy
aws iam create-policy \
    --policy-name JenkinsECREKSPolicy \
    --policy-document file://jenkins-iam-policy.json

# Create the IAM role with EC2 trust relationship
aws iam create-role \
    --role-name JenkinsEC2Role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": { "Service": "ec2.amazonaws.com" },
                "Action": "sts:AssumeRole"
            }
        ]
    }'

# Attach the policy to the role
aws iam attach-role-policy \
    --role-name JenkinsEC2Role \
    --policy-arn arn:aws:iam::<YOUR_ACCOUNT_ID>:policy/JenkinsECREKSPolicy

# Create an Instance Profile and add the role to it
aws iam create-instance-profile \
    --instance-profile-name JenkinsInstanceProfile

aws iam add-role-to-instance-profile \
    --instance-profile-name JenkinsInstanceProfile \
    --role-name JenkinsEC2Role
```

**Step 3: Attach the Instance Profile to the Jenkins EC2 Instance**

```bash
# If Jenkins is already running on an EC2 instance:
aws ec2 associate-iam-instance-profile \
    --instance-id i-0123456789abcdef0 \
    --iam-instance-profile Name=JenkinsInstanceProfile

# If launching a new Jenkins EC2 instance, include it at launch:
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.medium \
    --iam-instance-profile Name=JenkinsInstanceProfile \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxx \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=Jenkins-Server}]'
```

**Step 4: Grant Jenkins IAM Role Access to EKS**

The Jenkins role needs to be mapped in the EKS `aws-auth` ConfigMap:

```bash
# Edit the aws-auth ConfigMap
kubectl edit configmap aws-auth -n kube-system
```

Add the Jenkins role to the `mapRoles` section:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    # ... existing entries (DO NOT remove them) ...
    - rolearn: arn:aws:iam::<YOUR_ACCOUNT_ID>:role/JenkinsEC2Role
      username: jenkins
      groups:
        - system:masters
```

> **Why `system:masters`?** For a portfolio/dev project, this grants full cluster admin. In production, you'd create a more restrictive ClusterRole and ClusterRoleBinding.

---

## Part 3 — Kubernetes Manifests

All manifests are in the `k8s/` directory.

### 3.1 Namespace (`k8s/namespace.yaml`)

Isolates all resources under the `devops-platform` namespace:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: devops-platform
  labels:
    app: devops-platform
```

### 3.2 Django Secret (`k8s/django-secret.yaml`)

Stores the Django `SECRET_KEY` securely (not baked into the image):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: django-secrets
type: Opaque
stringData:
  secret-key: "super-secret-django-key-change-this-in-production-2024"
```

> In production, use **AWS Secrets Manager** with the **Kubernetes External Secrets Operator** instead.

### 3.3 Backend Deployment (`k8s/backend-deployment.yaml`)

Key features:

- **2 replicas** for high availability
- **Rolling update strategy** (`maxSurge: 1, maxUnavailable: 0`) for zero-downtime deployments
- **Resource limits** to prevent noisy-neighbor issues on the cluster
- **Readiness probe** to ensure traffic is only sent to healthy pods
- **Liveness probe** to auto-restart unhealthy pods (self-healing)
- **Secret injection** via `secretKeyRef`

### 3.4 Backend Service (`k8s/backend-service.yaml`)

- **ClusterIP** type — only accessible within the cluster (the frontend Nginx proxies to it)

### 3.5 Frontend Deployment (`k8s/frontend-deployment.yaml`)

Same patterns as the backend: 2 replicas, rolling updates, resource limits, probes.

### 3.6 Frontend Service (`k8s/frontend-service.yaml`)

- **ClusterIP** type — internal-only service, exposed publicly by the nginx ingress controller rather than by a direct AWS LoadBalancer on the frontend pod

### 3.7 Nginx Ingress (`k8s/ingress.yaml`)

Expose the app through the nginx ingress controller on EKS:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: devops-platform-ingress
  namespace: devops-platform
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  ingressClassName: nginx
  rules:
    - host: devops-platform.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
```

This pattern is the standard AWS EKS setup: the ingress controller creates the public ALB while the app services remain internal and only reachable through the ingress.

### 3.8 Apply Manually (for testing)

```bash
# Install nginx ingress controller in EKS
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply secret
kubectl apply -f k8s/django-secret.yaml -n devops-platform

# Deploy backend
kubectl apply -f k8s/backend-deployment.yaml -n devops-platform
kubectl apply -f k8s/backend-service.yaml -n devops-platform
kubectl apply -f k8s/backend-hpa.yaml -n devops-platform

# Deploy frontend
kubectl apply -f k8s/frontend-deployment.yaml -n devops-platform
kubectl apply -f k8s/frontend-service.yaml -n devops-platform
kubectl apply -f k8s/frontend-hpa.yaml -n devops-platform
kubectl apply -f k8s/ingress.yaml -n devops-platform

# Check status
kubectl get all -n devops-platform
kubectl get ingress -n devops-platform
kubectl get hpa -n devops-platform

# Get the public URL via the ingress controller
kubectl get svc ingress-nginx-controller -n ingress-nginx -o wide
# EXTERNAL-IP: a1b2c3d4e5f6-1234567890.us-east-1.elb.amazonaws.com
```

Map your DNS record (for example, `devops-platform.example.com`) to the ingress controller’s ALB or use a local hosts entry when testing in a private environment.

---

## Part 4 — Automated CI/CD (Jenkinsfile)

### 4.1 Pipeline Stages

The `Jenkinsfile` at the project root defines a **5-stage declarative pipeline**:

```
┌───────────┐     ┌───────────┐    ┌───────────┐     ┌───────────┐    ┌───────────┐
│  Stage 1  │───▶│  Stage 2  │───▶│  Stage 3  │───▶│  Stage 4  │───▶│  Stage 5  │
│ Checkout  │     │ Lint/Test │    │  Docker   │     │ Push ECR  │    │ Deploy to │
│           │     │ (parallel)│    │ Build+Tag │     │           │    │   EKS     │
│ git clone │     │ • Django  │    │ (parallel)│     │ docker    │    │ kubectl   │
│ short SHA │     │ • ESLint  │    │  backend  │     │ push      │    │ apply     │
└───────────┘     └───────────┘    └───────────┘     └───────────┘    └───────────┘
```

| Stage                   | What It Does                                                                | Key Commands                                      |
| ----------------------- | --------------------------------------------------------------------------- | ------------------------------------------------- |
| **Checkout**            | Clones the repo, extracts short Git SHA for image tagging                   | `git rev-parse --short HEAD`                      |
| **Lint & Test**         | Runs Django tests, ESLint, and Hadolint (Dockerfile linter) in parallel     | `python manage.py test`, `npx eslint`, `hadolint` |
| **Build & Push Images** | Kaniko builds both images in parallel and pushes SHA + `latest` tags to ECR | `/kaniko/executor --destination <ecr>:<sha>`      |
| **Deploy to EKS**       | Applies rendered manifests, HPAs, and verifies rollouts                     | `kubectl apply`, `kubectl rollout status`         |

### 4.2 Jenkins Setup Prerequisites

Jenkins now runs inside the existing EKS cluster. The controller is persistent, while each build uses an ephemeral Kubernetes worker pod. Kaniko builds and pushes images without Docker-in-Docker or a host Docker socket.

**Install the Jenkins controller and permissions:**

```bash
helm repo add jenkins https://charts.jenkins.io
helm repo update

kubectl create namespace jenkins
helm upgrade --install jenkins jenkins/jenkins \
  --namespace jenkins \
  --values k8s/jenkins-values.yaml \
  --set controller.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="arn:aws:iam::<YOUR_ACCOUNT_ID>:role/JenkinsEcrRole"

kubectl apply -f k8s/jenkins-agent-rbac.yaml -n jenkins
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/jenkins-deployer-rbac.yaml

kubectl get pods -n jenkins
kubectl get pvc -n jenkins
```

The `jenkins` service account needs an IAM role with ECR push permissions. The deployer `RoleBinding` grants it access only to the `devops-platform` namespace. Configure EKS Pod Identity or IRSA before running the pipeline.

**Install these tools only when Jenkins runs outside Kubernetes:**

```bash
# Docker (for building images)
sudo yum install -y docker
sudo systemctl start docker
sudo usermod -aG docker jenkins

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Node.js 20 (for frontend lint)
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install -y nodejs

# Python 3.12 (for backend tests)
sudo yum install -y python3.12 python3.12-venv
```

**Jenkins Credentials:**

In Jenkins → **Manage Jenkins** → **Credentials** → **Global**, add:

| ID               | Type        | Value                                               |
| ---------------- | ----------- | --------------------------------------------------- |
| `aws-account-id` | Secret Text | Your 12-digit AWS Account ID (e.g., `123456789012`) |

**Create the Pipeline Job:**

1. Jenkins → **New Item** → **Pipeline**
2. Name: `devops-platform`
3. Under **Pipeline**:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/<your-username>/devops-platform.git`
   - Branch: `*/main`
   - Script Path: `Jenkinsfile`
4. Under **Build Triggers**:
   - Check **GitHub hook trigger for GITScm polling**
5. Save

**GitHub Webhook:**

In your GitHub repo → **Settings** → **Webhooks** → **Add webhook**:

- Payload URL: `http://<jenkins-public-ip>:8080/github-webhook/`
- Content type: `application/json`
- Events: **Just the push event**

---

## Part 5 — Running the Full Pipeline

### 5.1 Push to GitHub

```bash
# Initialize the repo
cd Devops_platform
git init
git add .
git commit -m "feat: initial CI/CD pipeline with Django, React, EKS"

# Create the GitHub repo and push
git remote add origin https://github.com/<your-username>/devops-platform.git
git branch -M main
git push -u origin main
```

### 5.2 Trigger the Pipeline

- **Automatic**: The GitHub webhook fires on push, triggering Jenkins
- **Manual**: Jenkins → `devops-platform` job → **Build Now**

### 5.3 Verify the Deployment

```bash
# Check pods
kubectl get pods -n devops-platform
# NAME                        READY   STATUS    RESTARTS   AGE
# backend-7b8c9d4f5-x2kl9    1/1     Running   0          2m
# backend-7b8c9d4f5-m3np8    1/1     Running   0          2m
# frontend-5c6d7e8f9-q4rs2   1/1     Running   0          2m
# frontend-5c6d7e8f9-t5uv3   1/1     Running   0          2m

# Check the ingress and public ALB
kubectl get ingress -n devops-platform
kubectl get svc ingress-nginx-controller -n ingress-nginx
# Copy the external DNS name from the ingress controller service and open it in your browser,
# or use your DNS entry such as http://devops-platform.example.com

# Test the app through the ingress endpoint
curl -H "Host: devops-platform.example.com" http://<INGRESS-LB-DNS>/api/info/
curl -H "Host: devops-platform.example.com" http://<INGRESS-LB-DNS>/api/health/
curl -H "Host: devops-platform.example.com" http://<INGRESS-LB-DNS>/api/tasks/
```

### 5.4 Test Zero-Downtime Rolling Update

```bash
# Make a code change (e.g., update a task title in views.py)
git add .
git commit -m "feat: update default tasks"
git push

# Watch the rolling update in real-time
kubectl rollout status deployment/backend -n devops-platform -w

# In another terminal, continuously hit the health endpoint through the ingress
# You'll see zero failed requests during the update:
while true; do curl -s -H "Host: devops-platform.example.com" http://<INGRESS-LB-DNS>/api/health/ | jq .status; sleep 1; done
```

## License

MIT License — feel free to fork, modify, and use for your portfolio.

---

**Built with ❤️ for the DevOps community.**
