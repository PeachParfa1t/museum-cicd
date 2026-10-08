# Лабораторная работа 2 на MacBook

## Что добавлено

- Приложение Flask и Waitress запускается в контейнере `app` на внутреннем порту 8000.
- Контейнер `nginx` принимает запросы на `127.0.0.1:8081` и передаёт их приложению.
- База SQLite остаётся в `~/museum-deploy/shared/museum.db` из первой лабораторной. При обновлении образа она не удаляется.
- Существующий Jenkins Multibranch Pipeline получает новый `Jenkinsfile` из GitHub. Для `dev` и `feature/*` проходят тесты и сборка архива. Для `main` дополнительно собирается образ, запускаются контейнеры и проверяется сайт.

Это две службы в одной контейнерной сети. Бизнес-логика музея по-прежнему находится в одном Flask-приложении; отдельные микросервисы для экспонатов, залов и других сущностей в этой лабораторной не выделяются.

## Подготовка MacBook

1. Установить и открыть Docker Desktop. Проверить в терминале:

   ```bash
   docker version
   docker compose version
   ```

2. Убедиться, что Jenkins работает от того же пользователя macOS, который запустил Docker Desktop. Для проверки в Jenkins выполнить сборку `main` и посмотреть этап `Check environment`. Если Docker недоступен службе Jenkins, перезапустить Jenkins после запуска Docker Desktop:

   ```bash
   brew services restart jenkins-lts
   ```

3. Оставить работающий GitHub webhook и прежнюю Multibranch Pipeline `museum-cicd`. Менять URL ngrok не нужно, пока его публичный адрес не изменился. Docker не должен принимать webhook напрямую: GitHub направляет событие в Jenkins на `/github-webhook/`.

4. Убедиться, что свободно место для Docker-образов:

   ```bash
   docker system df
   ```

## Как ввести изменения через три ветки

Эти файлы добавляются к тому же репозиторию `PeachParfa1t/museum-cicd`. Скачайте архив изменений `museum_lab2_changes.zip` и распакуйте его в корень локального репозитория. Выполните команды из каталога проекта, заменив путь к архиву, если он сохранён не в `Downloads`:

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/lab2-containers
unzip -o "$HOME/Downloads/museum_lab2_changes.zip" -d .
git add .dockerignore Dockerfile compose.yaml nginx/default.conf scripts/deploy-container.sh Jenkinsfile README.md LAB2_GUIDE.md
git commit -m "ЛР2: контейнеры приложения и nginx"
git push -u origin feature/lab2-containers
```

Изменения в `feature/lab2-containers` и затем в `dev` должны пройти тесты без деплоя. Для переноса изменений:

```bash
git switch dev
git pull --ff-only origin dev
git merge feature/lab2-containers
git push origin dev
```

Убедиться, что сборка `dev` зелёная, а этапы `Build container`, `Deploy` и `Health check` пропущены. Затем:

```bash
git switch main
git pull --ff-only origin main
git merge dev
git push origin main
```

Push в `main` запускает новую сборку автоматически через webhook. Jenkins берёт `Jenkinsfile` именно из отправленного коммита. В интерфейсе самой задачи менять сценарий Pipeline вручную не нужно.

## Деплой и проверка

После успешной сборки `main` в обычном терминале Mac сначала задать переменные, используемые файлом Compose:

```bash
export DEPLOY_ROOT="$HOME/museum-deploy"
export HOST_UID="$(id -u)"
export HOST_GID="$(id -g)"
export IMAGE_TAG="$(docker inspect museum-archive-app-1 --format '{{.Config.Image}}' | cut -d: -f2)"
docker compose -f "$DEPLOY_ROOT/container/compose.yaml" ps
docker compose -f "$DEPLOY_ROOT/container/compose.yaml" logs --tail=50
curl -i http://127.0.0.1:8081/health
curl -I http://127.0.0.1:8081/
```

Успешный ответ `/health` содержит `"status":"ok"`. Сайт открывается по прежнему адресу http://127.0.0.1:8081. Первый контейнер `app` не публикует порт на Mac: попасть к нему снаружи можно через nginx.

Чтобы показать, что данные SQLite сохраняются, добавьте запись на сайте, отправьте следующий commit в `main`, дождитесь повторного деплоя и проверьте, что запись осталась. Файл базы хранится вне Docker-образа:

```bash
ls -l "$HOME/museum-deploy/shared/museum.db"
```

Простой способ остановить контейнеры после демонстрации:

```bash
docker compose -f "$DEPLOY_ROOT/container/compose.yaml" stop
```

Команда `down --volumes` для этого сценария не нужна: база подключена из каталога Mac.

## Скриншоты в отчёт

1. Три ветки `main`, `dev`, `feature/lab2-containers` на GitHub.
2. Успешные сборки `feature/lab2-containers` и `dev` с пропущенным деплоем.
3. Успешная сборка `main` с этапами `Build container`, `Deploy` и `Health check`.
4. Вывод `docker compose ... ps` с двумя работающими контейнерами.
5. Ответ `curl -i http://127.0.0.1:8081/health` и страница сайта.
6. Файл `nginx/default.conf` и файл базы вне контейнера.

## Если что-то не запустилось

- `docker: command not found`: Docker Desktop не установлен или команда `docker` недоступна в PATH службы Jenkins.
- `Cannot connect to the Docker daemon`: запустить Docker Desktop и проверить `docker version` в терминале; перезапустить Jenkins.
- `port is already allocated`: проверить `lsof -nP -iTCP:8081 -sTCP:LISTEN`. Старый сайт из первой лабораторной останавливается сценарием `deploy-container.sh` по файлу `~/museum-deploy/museum.pid`.
- `permission denied` для базы: проверить владельца `~/museum-deploy/shared` и учетную запись, от которой работает Jenkins. В контейнере приложение работает с UID/GID этой учетной записи.
- Для просмотра ошибок: экспортировать переменные из раздела «Деплой и проверка», затем выполнить `docker compose -f "$DEPLOY_ROOT/container/compose.yaml" logs --tail=100`.
