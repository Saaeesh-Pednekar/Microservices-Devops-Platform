pipeline {
    agent {
        kubernetes {
            defaultContainer 'tools'
            yaml '''
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: devops-platform
    component: jenkins-agent
spec:
  serviceAccountName: jenkins
  restartPolicy: Never
  containers:
    - name: tools
      image: alpine/k8s:1.31.0
      command: [/bin/sh]
      args: [-c, cat]
      tty: true
    - name: python
      image: python:3.12-slim
      command: [/bin/sh]
      args: [-c, cat]
      tty: true
    - name: node
      image: node:20-alpine
      command: [/bin/sh]
      args: [-c, cat]
      tty: true
    - name: hadolint
      image: hadolint/hadolint:latest-debian
      command: [/bin/sh]
      args: [-c, cat]
      tty: true
    - name: kaniko
      image: gcr.io/kaniko-project/executor:v1.23.2-debug
      command: [/busybox/sh]
      args: [-c, cat]
      tty: true
      volumeMounts:
        - name: kaniko-docker-config
          mountPath: /kaniko/.docker
  volumes:
    - name: kaniko-docker-config
      emptyDir: {}
'''
            workspaceVolume emptyDirWorkspaceVolume()
        }
    }

    environment {
        AWS_REGION         = 'us-east-1'
        AWS_ACCOUNT_ID     = credentials('aws-account-id')
        ECR_REGISTRY       = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        ECR_REPO_BACKEND   = "${ECR_REGISTRY}/devops-platform-backend"
        ECR_REPO_FRONTEND  = "${ECR_REGISTRY}/devops-platform-frontend"
        K8S_NAMESPACE      = 'devops-platform'
        IMAGE_TAG          = ''
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.IMAGE_TAG = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                    echo "Building images with tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Lint & Test') {
            parallel {
                stage('Backend Tests') {
                    steps {
                        container('python') {
                            dir('backend') {
                                sh '''
                                    python -m venv .venv
                                    . .venv/bin/activate
                                    pip install --quiet -r requirements.txt
                                    python manage.py check --deploy 2>&1 || true
                                    python manage.py test --verbosity=2
                                '''
                            }
                        }
                    }
                }
                stage('Frontend Lint') {
                    steps {
                        container('node') {
                            dir('frontend') {
                                sh '''
                                    npm ci --prefer-offline
                                    npx eslint src/ --max-warnings=0
                                '''
                            }
                        }
                    }
                }
                stage('Dockerfile Lint') {
                    steps {
                        container('hadolint') {
                            sh '''
                                hadolint backend/Dockerfile
                                hadolint frontend/Dockerfile
                            '''
                        }
                    }
                }
            }
        }

        stage('Build & Push Images') {
            parallel {
                stage('Build Backend') {
                    steps {
                        container('kaniko') {
                            sh '''
                                printf '{"credHelpers":{"%s":"ecr-login"}}' "$ECR_REGISTRY" > /kaniko/.docker/config.json
                                /kaniko/executor \
                                  --context "$WORKSPACE/backend" \
                                  --dockerfile "$WORKSPACE/backend/Dockerfile" \
                                  --destination "$ECR_REPO_BACKEND:$IMAGE_TAG" \
                                  --destination "$ECR_REPO_BACKEND:latest" \
                                  --build-arg "APP_VERSION=$IMAGE_TAG" \
                                  --cache=true
                            '''
                        }
                    }
                }
                stage('Build Frontend') {
                    steps {
                        container('kaniko') {
                            sh '''
                                printf '{"credHelpers":{"%s":"ecr-login"}}' "$ECR_REGISTRY" > /kaniko/.docker/config.json
                                /kaniko/executor \
                                  --context "$WORKSPACE/frontend" \
                                  --dockerfile "$WORKSPACE/frontend/Dockerfile" \
                                  --destination "$ECR_REPO_FRONTEND:$IMAGE_TAG" \
                                  --destination "$ECR_REPO_FRONTEND:latest" \
                                  --cache=true
                            '''
                        }
                    }
                }
            }
        }

        stage('Deploy to EKS') {
            steps {
                container('tools') {
                    sh '''
                        set -eu
                        SERVICE_ACCOUNT_TOKEN="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"
                        KUBE_CA=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
                        KUBE_SERVER="https://${KUBERNETES_SERVICE_HOST}:${KUBERNETES_SERVICE_PORT_HTTPS}"
                        KUBECTL="kubectl --server=$KUBE_SERVER --certificate-authority=$KUBE_CA --token=$SERVICE_ACCOUNT_TOKEN"

                        $KUBECTL apply -f k8s/django-secret.yaml -n "$K8S_NAMESPACE"

                        rm -rf rendered-k8s
                        mkdir rendered-k8s
                        cp k8s/backend-deployment.yaml k8s/backend-service.yaml k8s/backend-hpa.yaml rendered-k8s/
                        cp k8s/frontend-deployment.yaml k8s/frontend-service.yaml k8s/frontend-hpa.yaml rendered-k8s/
                        sed -i "s|image: .*devops-platform-backend:.*|image: $ECR_REPO_BACKEND:$IMAGE_TAG|" rendered-k8s/backend-deployment.yaml
                        sed -i "s|image: .*devops-platform-frontend:.*|image: $ECR_REPO_FRONTEND:$IMAGE_TAG|" rendered-k8s/frontend-deployment.yaml
                        sed -i "s|value: \"latest\"|value: \"$IMAGE_TAG\"|" rendered-k8s/backend-deployment.yaml

                        $KUBECTL apply -f rendered-k8s/backend-deployment.yaml -n "$K8S_NAMESPACE"
                        $KUBECTL apply -f rendered-k8s/backend-service.yaml -n "$K8S_NAMESPACE"
                        $KUBECTL apply -f rendered-k8s/backend-hpa.yaml -n "$K8S_NAMESPACE"
                        $KUBECTL apply -f rendered-k8s/frontend-deployment.yaml -n "$K8S_NAMESPACE"
                        $KUBECTL apply -f rendered-k8s/frontend-service.yaml -n "$K8S_NAMESPACE"
                        $KUBECTL apply -f rendered-k8s/frontend-hpa.yaml -n "$K8S_NAMESPACE"
                        $KUBECTL rollout status deployment/backend -n "$K8S_NAMESPACE" --timeout=120s
                        $KUBECTL rollout status deployment/frontend -n "$K8S_NAMESPACE" --timeout=120s
                        $KUBECTL get deployments,hpa -n "$K8S_NAMESPACE"
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully. Images deployed to EKS.'
        }
        failure {
            echo 'Pipeline failed. Check the stage logs for details.'
        }
        always {
            cleanWs()
        }
    }
}