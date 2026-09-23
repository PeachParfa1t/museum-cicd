pipeline {
    agent any

    environment {
        PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        DEPLOY_URL = "http://127.0.0.1:8081"
        APP_PORT = "8081"
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
                        app scripts requirements.txt run.py wsgi.py \
                        pyproject.toml README.md
                '''

                archiveArtifacts artifacts: "build/*.tar.gz",
                                 fingerprint: true
            }
        }

        stage("Deploy") {
            when {
                branch "main"
            }

            steps {
                sh '''
                    chmod +x scripts/deploy.sh
                    scripts/deploy.sh
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
                    tail -n 100 "$HOME/museum-deploy/museum.log" || true
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
