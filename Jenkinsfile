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
                '''
            }
        }

        stage("Tests") {
            steps {
                sh '''
                    .venv/bin/python -m pytest --junitxml=test-results.xml
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
                    .venv/bin/python -m compileall -q app run.py wsgi.py
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

        stage("Build container") {
            steps {
                script {
                    def safeBranch = env.BRANCH_NAME.replaceAll('[^A-Za-z0-9_.-]', '-')
                    def commitId = sh(script: 'git rev-parse --short=12 HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG = "${safeBranch}-${commitId}"
                    env.IMAGE_REF = "localhost:5001/museum-archive:${env.IMAGE_TAG}"
                }
                sh '''
                    docker build -t "$IMAGE_REF" .
                '''
            }
        }

        stage("Publish image") {
            steps {
                sh '''
                    docker push "$IMAGE_REF"
                '''
            }
        }

        stage("Deploy") {
            when {
                branch "main"
            }

            steps {
                sh '''
                    bash scripts/deploy-container.sh
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
                        if curl --fail --silent "$DEPLOY_URL/health"; then
                            echo
                            echo "Сайт успешно развёрнут"
                            exit 0
                        fi

                        echo "Ожидание запуска сайта..."
                        sleep 2
                    done

                    echo "Сайт не запустился"
                    export DEPLOY_ROOT="$HOME/museum-deploy"
                    export HOST_UID="$(id -u)"
                    export HOST_GID="$(id -g)"
                    docker compose -f "$HOME/museum-deploy/container/compose.yaml" logs --tail=100 || true
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
