pipeline {
    agent any

    environment {
        PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        DEPLOY_URL = "http://127.0.0.1:8081"
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: "10"))
        skipDefaultCheckout(true)
    }

    triggers {
        githubPush()
    }

    stages {
        stage("Checkout") {
            steps {
                checkout scm
                sh '''
                    echo "Ветка: $BRANCH_NAME"
                    echo "Коммит: $GIT_COMMIT"
                '''
            }
        }

        stage("Check environment") {
            steps {
                sh '''
                    git --version
                    python3 --version
                    docker --version
                    docker compose version
                '''
            }
        }

        stage("Install dependencies") {
            steps {
                sh '''
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/python -m pip install -r requirements.txt
                    .venv/bin/python -m pip install -r services/users/requirements.txt
                '''
            }
        }

        stage("Tests") {
            steps {
                sh '''
                    PYTHONPATH="services/users:$PYTHONPATH" .venv/bin/python -m pytest tests services/users/tests --junitxml=test-results.xml
                '''
            }

            post {
                always {
                    junit testResults: "test-results.xml",
                          allowEmptyResults: true
                }
            }
        }

        stage("Validate sources") {
            steps {
                sh '''
                    .venv/bin/python -m compileall -q app run.py wsgi.py services/users/users_service services/users/wsgi.py
                '''
            }
        }

        stage("Check registry") {
            steps {
                sh '''
                    curl --fail --silent http://127.0.0.1:5001/v2/ > /dev/null
                '''
            }
        }

        stage("Build images") {
            steps {
                script {
                    def safeBranch = env.BRANCH_NAME.replaceAll('[^A-Za-z0-9_.-]', '-')
                    def commitId = sh(script: 'git rev-parse --short=12 HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG = "${safeBranch}-${commitId}"
                }
                sh '''
                    docker build -t "localhost:5001/museum-core:$IMAGE_TAG" .
                    docker build -f services/users/Dockerfile -t "localhost:5001/museum-users:$IMAGE_TAG" .
                '''
            }
        }

        stage("Publish images") {
            steps {
                sh '''
                    docker push "localhost:5001/museum-core:$IMAGE_TAG"
                    docker push "localhost:5001/museum-users:$IMAGE_TAG"
                '''
            }
        }

        stage("Deploy to Kubernetes") {
            when {
                branch "main"
            }

            steps {
                sh '''
                    bash scripts/deploy-k8s.sh
                '''
            }
        }

        stage("Health check") {
            when {
                branch "main"
            }

            steps {
                sh '''
                    for attempt in $(seq 1 15); do
                        if curl --fail --silent "$DEPLOY_URL/health" > /dev/null && \
                           curl --fail --silent "$DEPLOY_URL/users-health" > /dev/null; then
                            echo "Оба сервиса доступны через nginx: $DEPLOY_URL"
                            exit 0
                        fi

                        echo "Ожидание запуска сайта..."
                        sleep 2
                    done

                    echo "Сервисы Kubernetes не готовы"
                    kubectl --context kind-museum-lab3 -n museum get pods || true
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline завершён успешно"
        }

        failure {
            echo "Pipeline завершился с ошибкой"
        }
    }
}
