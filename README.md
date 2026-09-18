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
9. [Part 6 — Interview Talking Points](#part-6--interview-talking-points)
10. [Cleanup](#cleanup)

---

## Architecture Overview

```
 Developer          GitHub              Jenkins             AWS ECR            AWS EKS
 ┌───────┐      ┌─────────────┐      ┌──────────────┐     ┌────────────┐     ┌──────────────┐
 │  Git  │────▶│  Repository │ ────▶│   Pipeline   │───▶│   Docker   │───▶ │  Kubernetes  │
 │ Push  │      │  (Webhook)  │      │              │     │  Registry  │     │   Cluster    │
 └───────┘      └─────────────┘      │  1. Checkout │     └────────────┘     │              │
                                     │  2. Lint/Test│                        │  ┌────────┐  │
                                     │  3. Build    │                        │  │Backend │  │
                                     │  4. Push ECR │                        │  │ (x2)   │  │
                                     │  5. Deploy   │                        │  ├────────┤  │
                                     └──────────────┘                        │  │Frontend│  │
                                            │                                │  │ (x2)   │  │
                                       IAM Instance                          │  └────────┘  │
                                         Profile                             │      │       │
                                   (No hardcoded keys!)                      │  LoadBalancer│
                                                                             └──────┬───────┘
                                                                                    │
                                                                              Public Internet
```

**How it works:**

1. Developer pushes code to GitHub
2. GitHub webhook triggers Jenkins pipeline
3. Jenkins runs lint/tests, builds Docker images, pushes to ECR
4. Jenkins updates Kubernetes deployments on EKS
5. EKS performs zero-downtime rolling updates
6. LoadBalancer exposes the app to the internet

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
│   ├── backend-service.yaml
│   ├── frontend-deployment.yaml
│   └── frontend-service.yaml
├── Jenkinsfile                 # Declarative CI/CD pipeline
├── .gitignore
└── README.md                   # ← You are here
```

---

## Prerequisites

Install these tools on your local machine before starting:

| Tool | Version | Purpose |
|------|---------|---------|
| [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) | ≥ 2.x | Interact with AWS services |
| [eksctl](https://eksctl.io/installation/) | ≥ 0.190.0 | Create and manage EKS clusters |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | ≥ 1.28 | Manage Kubernetes resources |
| [Docker](https://docs.docker.com/get-docker/) | ≥ 24.x | Build container images |
| [Node.js](https://nodejs.org/) | ≥ 20.x | Build frontend |
| [Python](https://www.python.org/) | ≥ 3.12 | Run backend |
| [Git](https://git-scm.com/) | ≥ 2.x | Version control |

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

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health/` | GET | Health check for K8s probes |
| `/api/info/` | GET | App version, hostname, environment, uptime |
| `/api/tasks/` | GET | List all tasks |
| `/api/tasks/add/` | POST | Create a new task |
| `/api/tasks/toggle/<id>/` | PATCH | Toggle task completion |
| `/api/tasks/delete/<id>/` | DELETE | Delete a task |

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

| Flag | Purpose |
|------|---------|
| `--version 1.31` | Kubernetes version |
| `--node-type t3.medium` | 2 vCPU, 4GB RAM — good for dev/demo |
| `--nodes 2` | 2 worker nodes |
| `--nodes-min 1 --nodes-max 3` | Autoscaling range |
| `--managed` | AWS-managed node group (auto-patched) |
| `--with-oidc` | Enables IRSA (IAM Roles for Service Accounts) |
| `--full-ecr-access` | Nodes can pull images from ECR |

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
            "Action": [
                "eks:DescribeCluster",
                "eks:ListClusters"
            ],
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

- **LoadBalancer** type — AWS provisions a Classic Load Balancer and assigns a public DNS name

### 3.7 Apply Manually (for testing)

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply secret
kubectl apply -f k8s/django-secret.yaml -n devops-platform

# Deploy backend
kubectl apply -f k8s/backend-deployment.yaml -n devops-platform
kubectl apply -f k8s/backend-service.yaml -n devops-platform

# Deploy frontend
kubectl apply -f k8s/frontend-deployment.yaml -n devops-platform
kubectl apply -f k8s/frontend-service.yaml -n devops-platform

# Check status
kubectl get all -n devops-platform

# Get the public URL
kubectl get svc frontend-service -n devops-platform -o wide
# EXTERNAL-IP: a1b2c3d4e5f6-1234567890.us-east-1.elb.amazonaws.com
```

---

## Part 4 — Automated CI/CD (Jenkinsfile)

### 4.1 Pipeline Stages

The `Jenkinsfile` at the project root defines a **5-stage declarative pipeline**:

```
┌───────────┐     ┌───────────┐    ┌───────────┐     ┌───────────┐    ┌───────────┐
│  Stage 1  │───▶│  Stage 2  │───▶│  Stage 3  │───▶│  Stage 4  │───▶│  Stage 5  │
│ Checkout  │     │ Lint/Test │    │  Docker   │     │ Push ECR  │    │ Deploy to │
│           │     │ (parallel)│    │ Build+Tag │     │           │    │   EKS     │
│ git clone │     │ • Django  │    │ (parallel)│     │ ecr login │    │ kubeconfig│
│ short SHA │     │ • ESLint  │    │  backend  │     │ docker    │    │ kubectl   │
│           │     │ • hadolint│    │  frontend │     │ push      │    │ apply     │
└───────────┘     └───────────┘    └───────────┘     └───────────┘    └───────────┘
```

| Stage | What It Does | Key Commands |
|-------|-------------|--------------|
| **Checkout** | Clones the repo, extracts short Git SHA for image tagging | `git rev-parse --short HEAD` |
| **Lint & Test** | Runs Django tests, ESLint, and Hadolint (Dockerfile linter) in parallel | `python manage.py test`, `npx eslint`, `hadolint` |
| **Docker Build & Tag** | Builds both images in parallel, tags with SHA + `latest` | `docker build -t <ecr>:<sha> .` |
| **Push to ECR** | Authenticates to ECR and pushes all 4 image tags | `aws ecr get-login-password \| docker login` |
| **Deploy to EKS** | Updates kubeconfig, patches manifests with new tag, applies via kubectl, verifies rollout | `kubectl apply`, `kubectl rollout status` |

### 4.2 Jenkins Setup Prerequisites

**Install on the Jenkins server:**

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

| ID | Type | Value |
|----|------|-------|
| `aws-account-id`  | Secret Text | Your 12-digit AWS Account ID (e.g., `123456789012`) |

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

# Get the public URL
kubectl get svc frontend-service -n devops-platform
# Copy the EXTERNAL-IP and open in your browser

# Test the API directly
curl http://<EXTERNAL-IP>/api/info/
curl http://<EXTERNAL-IP>/api/health/
curl http://<EXTERNAL-IP>/api/tasks/
```

### 5.4 Test Zero-Downtime Rolling Update

```bash
# Make a code change (e.g., update a task title in views.py)
git add .
git commit -m "feat: update default tasks"
git push

# Watch the rolling update in real-time
kubectl rollout status deployment/backend -n devops-platform -w

# In another terminal, continuously hit the health endpoint
# You'll see zero failed requests during the update:
while true; do curl -s http://<EXTERNAL-IP>/api/health/ | jq .status; sleep 1; done
```

---

## Part 6 — Interview Talking Points

Use these points to explain this project with confidence during technical interviews:

### 🔐 Secure Cloud Authentication (IAM Instance Profiles)

> "I configured the Jenkins EC2 instance with an **IAM Instance Profile** instead of hardcoding AWS access keys. This means the EC2 instance automatically receives temporary, rotating credentials from the AWS metadata service. It eliminates the risk of key leakage in source code or build logs, and follows the **principle of least privilege** — the policy only grants ECR push/pull and EKS describe permissions."

### ♻️ Self-Healing Infrastructure

> "Kubernetes provides **self-healing** through liveness probes and the restart policy. Each pod has a liveness probe that hits `/api/health/` every 20 seconds. If a pod fails to respond 5 times in a row, Kubernetes automatically kills and recreates it — no human intervention needed. I also set **resource limits** (CPU/Memory) so a single misbehaving pod can't consume all cluster resources and take down other services."

### 🔄 Zero-Downtime Rolling Updates

> "The deployment uses a **RollingUpdate strategy** with `maxSurge: 1` and `maxUnavailable: 0`. This means Kubernetes creates a new pod with the updated image *before* terminating an old one. Combined with **readiness probes**, traffic is never routed to a pod that hasn't passed its health check. I verified this by running a continuous `curl` loop during a deployment — zero failed requests."

### 🏗️ Immutable, Traceable Deployments

> "Every Docker image is tagged with the **Git commit SHA** (not `latest`), making each deployment fully traceable back to its exact source code. If a bug is introduced, I can identify the exact commit, and Kubernetes makes it trivial to **rollback** with `kubectl rollout undo`. The multi-stage Dockerfiles also follow security best practices: non-root users, minimal base images, and no build tools in the production layer."

---

## Cleanup

**⚠️ IMPORTANT: Delete resources to avoid AWS charges.**

```bash
# 1. Delete the Kubernetes resources
kubectl delete namespace devops-platform

# 2. Delete the EKS cluster (this takes ~10 minutes)
eksctl delete cluster --name devops-platform-cluster --region us-east-1

# 3. Delete ECR repositories
aws ecr delete-repository \
    --repository-name devops-platform-backend \
    --region us-east-1 --force

aws ecr delete-repository \
    --repository-name devops-platform-frontend \
    --region us-east-1 --force

# 4. Delete IAM resources
aws iam detach-role-policy \
    --role-name JenkinsEC2Role \
    --policy-arn arn:aws:iam::<YOUR_ACCOUNT_ID>:policy/JenkinsECREKSPolicy

aws iam remove-role-from-instance-profile \
    --instance-profile-name JenkinsInstanceProfile \
    --role-name JenkinsEC2Role

aws iam delete-instance-profile --instance-profile-name JenkinsInstanceProfile
aws iam delete-role --role-name JenkinsEC2Role
aws iam delete-policy --policy-arn arn:aws:iam::<YOUR_ACCOUNT_ID>:policy/JenkinsECREKSPolicy
```

---

## License

MIT License — feel free to fork, modify, and use for your portfolio.

---

**Built with ❤️ for the DevOps community.**