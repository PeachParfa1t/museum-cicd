# ЛР2: Docker-образы как артефакты

Jenkins теперь выполняет `docker build` и `docker push` для `feature/*`, `dev` и `main`. Образ публикуется в локальном Docker Registry на Mac с тегом `<ветка>-<12 символов коммита>`; например, `localhost:5001/museum-archive:main-3e1bb25dcc2a`. Для `main` сценарий деплоя отдельно выполняет `docker compose pull app` и запускает полученный образ. Архив `.tar.gz` больше не создаётся; старые архивы в истории прежних сборок останутся до очистки истории Jenkins.

Registry слушает только `127.0.0.1:5001` на этом Mac. Для лабораторной на одном компьютере логин не нужен. Этот вариант не публикует образ в интернете и не является развёртыванием на отдельном сервере. Если преподаватель требует удалённый registry или удалённый сервер, понадобится дополнительно выбрать внешний registry, настроить Jenkins Credentials и изменить адрес образа в `Jenkinsfile` и `compose.yaml`.

## 1. Подготовить локальный registry

Сначала запустите Docker Desktop. В терминале Mac из корня проекта с файлом `registry.compose.yaml` выполните:

```bash
mkdir -p "$HOME/museum-deploy/registry"
DEPLOY_ROOT="$HOME/museum-deploy" docker compose -f registry.compose.yaml up -d
curl -i http://127.0.0.1:5001/v2/
```

Ожидаемый HTTP-статус — `200 OK`, обычно с телом `{}`. Хранилище находится в `~/museum-deploy/registry`, поэтому при пересоздании контейнера уже отправленные образы сохраняются. Если порт занят, найдите процесс `lsof -nP -iTCP:5001 -sTCP:LISTEN`. Registry должен быть доступен в момент каждой сборки Jenkins; Docker Desktop также должен работать.

## 2. Добавить файлы в уже существующий репозиторий

Распакуйте архив изменений для registry в корень локального `museum_cicd` (там, где лежит `Jenkinsfile`). Новую ветку от актуального `main` можно назвать `feature/registry`; если уже работаете в другой своей feature-ветке, используйте её. Пример команд из корня репозитория:

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/registry
git add Jenkinsfile compose.yaml registry.compose.yaml scripts/deploy-container.sh README.md LAB2_GUIDE.md REGISTRY_GUIDE.md
git commit -m "ЛР2: публиковать образы в registry"
git push -u origin feature/registry
```

После push ветки `feature/registry` в Jenkins Multibranch Pipeline дождитесь `Tests`, `Build container` и `Publish image`. `Deploy` и `Health check` должны быть пропущены. Затем перенесите изменения:

```bash
git switch dev
git pull --ff-only origin dev
git merge feature/registry
git push origin dev
```

После зелёной сборки `dev` и пропущенного `Deploy`:

```bash
git switch main
git pull --ff-only origin main
git merge dev
git push origin main
```

Push в `main` запускает через прежний GitHub webhook сборку, публикацию образа, загрузку образа из registry, запуск Compose и проверку сайта. Адрес nginx и сайта остаётся `http://127.0.0.1:8081/`. URL ngrok и настройки Multibranch Pipeline менять не требуется, если прежний webhook уже работает. Коммит и push в `dev` или `feature/*` не обновляют работающий сайт.

## 3. Показать преподавателю артефакт

После сборок:

```bash
curl http://127.0.0.1:5001/v2/_catalog
curl http://127.0.0.1:5001/v2/museum-archive/tags/list
curl -i http://127.0.0.1:8081/health
```

Во втором ответе должны появиться теги `feature-registry-...`, `dev-...` и `main-...`. Вместе с этапом `Publish image` (`docker push`) в Jenkins это подтверждает, что результат сборки хранится в registry. `docker images` показывает лишь локальный кэш Docker и сам по себе публикацию не подтверждает. Во время деплоя Jenkins выполняет `docker compose pull app`; в выводе стадии `Deploy` можно показать загрузку образа из registry. Для демонстрации тега запущенного приложения:

```bash
docker inspect museum-archive-app-1 --format '{{.Config.Image}}'
```

Если `docker push` или `docker compose pull app` сообщают `connection refused`, проверьте `curl -i http://127.0.0.1:5001/v2/`, Docker Desktop и контейнер registry:

```bash
DEPLOY_ROOT="$HOME/museum-deploy" docker compose -f registry.compose.yaml ps
DEPLOY_ROOT="$HOME/museum-deploy" docker compose -f registry.compose.yaml logs --tail=50
```
