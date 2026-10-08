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

        stage("Build package") {
            steps {
                sh '''
                    .venv/bin/python -m compileall -q app run.py wsgi.py
                    mkdir -p build
                    tar --exclude="*/__pycache__" --exclude="*.pyc" \
                        -czf "build/museum-archive-${BUILD_NUMBER}.tar.gz" \
                        app scripts nginx requirements.txt run.py wsgi.py \
                        pyproject.toml README.md LAB2_GUIDE.md \
                        Dockerfile compose.yaml .dockerignore
                '''

                archiveArtifacts artifacts: "build/*.tar.gz",
                                 fingerprint: true
            }
        }

        stage("Build container") {
            when {
                branch "main"
            }

            steps {
                sh '''
                    IMAGE_TAG="$(git rev-parse --short=12 HEAD)"
                    docker build -t "museum-archive:$IMAGE_TAG" .
                '''
            }
        }

        stage("Deploy") {
            when {
                branch "main"
            }

            steps {
                sh '''
                    export IMAGE_TAG="$(git rev-parse --short=12 HEAD)"
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
                    export IMAGE_TAG="$(git rev-parse --short=12 HEAD)"
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
