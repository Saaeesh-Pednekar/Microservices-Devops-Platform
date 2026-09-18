pipeline {
    agent any

    environment {
        AWS_REGION         = 'us-east-1'
        AWS_ACCOUNT_ID     = credentials('aws-account-id')        // Jenkins credential (Secret Text)
        ECR_REPO_BACKEND   = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/devops-platform-backend"
        ECR_REPO_FRONTEND  = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/devops-platform-frontend"
        EKS_CLUSTER_NAME   = 'devops-platform-cluster'
        K8S_NAMESPACE      = 'devops-platform'
        IMAGE_TAG           = "${GIT_COMMIT}"
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {
        // STAGE 1: Checkout
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.IMAGE_TAG = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                    echo "Building images with tag: ${env.IMAGE_TAG}"
                }
            }
        }

        // STAGE 2: Lint & Test
        stage('Lint & Test') {
            parallel {
                stage('Backend Tests') {
                    steps {
                        dir('backend') {
                            sh '''
                                python3 -m venv .venv
                                . .venv/bin/activate
                                pip install --quiet -r requirements.txt
                                python manage.py check --deploy 2>&1 || true
                                python manage.py test --verbosity=2
                            '''
                        }
                    }
                }
                stage('Frontend Lint') {
                    steps {
                        dir('frontend') {
                            sh '''
                                npm ci --prefer-offline
                                npx eslint src/ --max-warnings=0 || echo "Lint warnings found"
                            '''
                        }
                    }
                }
                stage('Dockerfile Lint') {
                    steps {
                        sh '''
                            echo "--- Linting backend Dockerfile ---"
                            docker run --rm -i hadolint/hadolint < backend/Dockerfile || true
                            echo "--- Linting frontend Dockerfile ---"
                            docker run --rm -i hadolint/hadolint < frontend/Dockerfile || true
                        '''
                    }
                }
            }
        }

        // STAGE 3: Docker Build & Tag
        stage('Docker Build & Tag') {
            parallel {
                stage('Build Backend') {
                    steps {
                        dir('backend') {
                            sh """
                                docker build \
                                    --build-arg APP_VERSION=${env.IMAGE_TAG} \
                                    -t ${ECR_REPO_BACKEND}:${env.IMAGE_TAG} \
                                    -t ${ECR_REPO_BACKEND}:latest \
                                    .
                            """
                        }
                    }
                }
                stage('Build Frontend') {
                    steps {
                        dir('frontend') {
                            sh """
                                docker build \
                                    -t ${ECR_REPO_FRONTEND}:${env.IMAGE_TAG} \
                                    -t ${ECR_REPO_FRONTEND}:latest \
                                    .
                            """
                        }
                    }
                }
            }
        }

        // STAGE 4: Push to Amazon ECR
        stage('Push to ECR') {
            steps {
                sh """
                    # Authenticate Docker to Amazon ECR
                    aws ecr get-login-password --region ${AWS_REGION} \
                        | docker login --username AWS \
                          --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

                    # Push Backend images
                    docker push ${ECR_REPO_BACKEND}:${env.IMAGE_TAG}
                    docker push ${ECR_REPO_BACKEND}:latest

                    # Push Frontend images
                    docker push ${ECR_REPO_FRONTEND}:${env.IMAGE_TAG}
                    docker push ${ECR_REPO_FRONTEND}:latest
                """
            }
        }

        // STAGE 5: Deploy to EKS
        stage('Deploy to EKS') {
            steps {
                sh """
                    # Configure kubectl to use the EKS cluster
                    aws eks update-kubeconfig \
                        --name ${EKS_CLUSTER_NAME} \
                        --region ${AWS_REGION}

                    # Create namespace if it doesn't exist
                    kubectl apply -f k8s/namespace.yaml

                    # Apply the Kubernetes secret
                    kubectl apply -f k8s/django-secret.yaml -n ${K8S_NAMESPACE}

                    # Update image tags in deployment manifests
                    sed -i "s|image: .*devops-platform-backend:.*|image: ${ECR_REPO_BACKEND}:${env.IMAGE_TAG}|g" k8s/backend-deployment.yaml
                    sed -i "s|image: .*devops-platform-frontend:.*|image: ${ECR_REPO_FRONTEND}:${env.IMAGE_TAG}|g" k8s/frontend-deployment.yaml

                    # Update APP_VERSION env var
                    sed -i "s|value: \"latest\"|value: \"${env.IMAGE_TAG}\"|g" k8s/backend-deployment.yaml

                    # Apply all Kubernetes manifests
                    kubectl apply -f k8s/backend-deployment.yaml -n ${K8S_NAMESPACE}
                    kubectl apply -f k8s/backend-service.yaml   -n ${K8S_NAMESPACE}
                    kubectl apply -f k8s/frontend-deployment.yaml -n ${K8S_NAMESPACE}
                    kubectl apply -f k8s/frontend-service.yaml   -n ${K8S_NAMESPACE}

                    # Verify rollout
                    kubectl rollout status deployment/backend  -n ${K8S_NAMESPACE} --timeout=120s
                    kubectl rollout status deployment/frontend -n ${K8S_NAMESPACE} --timeout=120s

                    echo "============================================"
                    echo "  Deployment Successful!"
                    echo "============================================"
                    kubectl get services -n ${K8S_NAMESPACE}
                """
            }
        }
    }

    post {
        success {
            echo '✅ Pipeline completed successfully! Application deployed to EKS.'
        }
        failure {
            echo '❌ Pipeline failed. Check the logs above for errors.'
        }
        always {
            // Clean up Docker images to save disk space on the Jenkins server
            sh '''
                docker image prune -f || true
            '''
            cleanWs()
        }
    }
}
