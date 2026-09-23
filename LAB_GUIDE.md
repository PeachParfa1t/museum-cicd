# Лабораторная работа CI CD без контейнеров

## Итоговая схема

Разработчик изменяет код в отдельной ветке и отправляет commit в GitHub. GitHub Webhook уведомляет Jenkins. Jenkins скачивает commit, создаёт виртуальное окружение, запускает тесты и формирует архив сборки. Для веток `dev` и `feature/*` работа заканчивается после CI. Для `main` Jenkins дополнительно копирует release в `~/museum-deploy`, перезапускает Waitress и проверяет `/health`.

Production-сайт работает на http://127.0.0.1:8081. Локальный запуск разработчика работает отдельно на http://127.0.0.1:5050.

## 1 Установка инструментов

```bash
brew install git python jenkins-lts ngrok
```

Проверка:

```bash
git --version
python3 --version
ngrok version
```

## 2 Проверка проекта

```bash
cd "/путь/к/museum_cicd"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
python run.py
```

Открыть http://127.0.0.1:5050. Остановить локальный сервер сочетанием `Control C`.

## 3 Проверка production развёртывания

```bash
chmod +x scripts/deploy.sh scripts/stop.sh
BUILD_NUMBER=manual-1 APP_PORT=8081 scripts/deploy.sh
curl http://127.0.0.1:8081/health
```

Открыть http://127.0.0.1:8081. После проверки остановить:

```bash
scripts/stop.sh
```

## 4 Репозиторий GitHub

Создать пустой публичный репозиторий `museum-cicd`, не добавляя README или `.gitignore` через GitHub.

```bash
git init
git branch -M main
git add .
git commit -m "Initial museum archive with Jenkins pipeline"
git remote add origin https://github.com/ЛОГИН/museum-cicd.git
git push -u origin main
```

Создать остальные ветки:

```bash
git switch -c dev
git push -u origin dev
git switch -c feature/change-title
git push -u origin feature/change-title
git switch main
```

## 5 Установка Jenkins

```bash
brew services start jenkins-lts
```

Открыть http://localhost:8080. Начальный пароль:

```bash
cat ~/.jenkins/secrets/initialAdminPassword
```

Выбрать `Install suggested plugins`, создать администратора и установить через `Manage Jenkins` дополнительные плагины:

- Git;
- Pipeline;
- GitHub;
- GitHub Branch Source;
- JUnit;
- Credentials Binding.

## 6 Multibranch Pipeline

В Jenkins выбрать `New Item`, указать имя `museum-cicd`, выбрать `Multibranch Pipeline`.

В `Branch Sources` выбрать `GitHub`, указать публичный адрес репозитория и оставить `Credentials` равным `none`. В `Build Configuration` выбрать `by Jenkinsfile`, а в `Script Path` указать `Jenkinsfile`.

После сохранения Jenkins должен обнаружить `main`, `dev` и `feature/change-title`. Первый успешный запуск `main` развернёт сайт на порту 8081.

## 7 Туннель и Webhook

Создать аккаунт ngrok и добавить выданный токен:

```bash
ngrok config add-authtoken "ТОКЕН"
ngrok http 8080
```

Скопировать публичный HTTPS адрес. В Jenkins открыть `Manage Jenkins`, затем `System` и указать его в `Jenkins URL`.

В GitHub открыть `Settings`, `Webhooks`, `Add webhook` и заполнить:

- Payload URL: `https://АДРЕС-NGROK/github-webhook/`;
- Content type: `application/json`;
- Event: `Just the push event`;
- Active: включено.

После создания GitHub должен показать зелёную доставку `ping`.

## 8 Демонстрация CI

```bash
git switch feature/change-title
```

В `app/templates/index.html` изменить текст `Цифровой фонд` на `Цифровой музейный фонд`. Сайт на порту 8081 измениться не должен.

```bash
git add app/templates/index.html
git commit -m "Change museum heading"
```

После commit сайт всё ещё не меняется. Затем выполнить:

```bash
git push
```

Webhook запускает ветку `feature/change-title`. Jenkins выполняет тесты и создаёт архив, но стадии `Deploy` и `Health check` пропускаются. Production-сайт не меняется.

## 9 Проверка dev

```bash
git switch dev
git merge --no-ff feature/change-title -m "Merge feature into dev"
git push
```

Для `dev` Jenkins снова выполняет CI без развёртывания. Сайт на порту 8081 остаётся прежним.

## 10 Демонстрация CD

```bash
git switch main
git merge --no-ff dev -m "Release updated museum heading"
git push
```

Для `main` Jenkins выполняет все стадии, включая `Deploy` и `Health check`. После зелёной сборки обновить http://127.0.0.1:8081. Новая надпись должна появиться только теперь.

## 11 Что сохраняет deploy script

- Releases: `~/museum-deploy/releases`.
- Активная версия: `~/museum-deploy/current`.
- Production SQLite: `~/museum-deploy/shared/museum.db`.
- Production Python: `~/museum-deploy/venv`.
- PID процесса: `~/museum-deploy/museum.pid`.
- Лог сервера: `~/museum-deploy/museum.log`.

Посмотреть лог:

```bash
tail -n 100 ~/museum-deploy/museum.log
```

Остановить сайт:

```bash
scripts/stop.sh
```

## 12 Материалы для отчёта

Сделать скриншоты сайта, пяти CRUD-разделов, структуры проекта, трёх веток, истории коммитов, Jenkinsfile, настроек Multibranch Pipeline, зелёного Webhook, результатов тестов, пропущенной стадии Deploy для feature и выполненной стадии Deploy для main. Отдельно показать сайт до push в main и после успешного CD.
