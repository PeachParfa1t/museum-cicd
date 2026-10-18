# Лабораторная работа № 3: музейный архив в Kubernetes

## Что изменилось по сравнению с лабораторной № 2

Приложение разделено **в коде и при запуске** на два независимых серверных сервиса:

| Сервис | Что делает | Исходники | База данных | Образ в локальном Registry |
| --- | --- | --- | --- | --- |
| `museum-core` | Главная страница, экспонаты, коллекции, залы, сотрудники, события | `app/`, корневой `Dockerfile` | `~/museum-deploy/shared/museum.db` | `museum-core:<ветка>-<коммит>` |
| `museum-users` | CRUD пользователей через `/api/users` | `services/users/`, свой `Dockerfile` | `~/museum-deploy/users/users.db` | `museum-users:<ветка>-<коммит>` |

«Сотрудники» — учёт работников музея из первой лабораторной. «Пользователи» — отдельный реестр посетителей или клиентов, без входа и паролей. Код пользователей **не импортирует** `app` и не открывает музейную базу. Браузер обращается к nginx по `http://127.0.0.1:8081`. nginx передаёт `/api/users` в `museum-users`, а страницу и остальной API — в `museum-core`. Обе службы работают на собственном внутреннем порту 8000; это разные Pod, конфликта портов нет.

kind создаёт один узел Kubernetes внутри Docker Desktop на Mac. `Deployment` поддерживает по две реплики `museum-core`, `museum-users` и nginx; у каждого Deployment свой `ReplicaSet`. `Service` направляет запросы на готовые реплики. При удалении одного Pod его ReplicaSet создаёт новый. Данные двух сервисов находятся в отдельных постоянных томах на Mac и сохраняются при замене Pod. Один узел демонстрирует восстановление **Pod**, но не переживёт выключение Mac или потерю всего узла. SQLite с двумя репликами здесь подходит для учебной демонстрации на одном узле; для нескольких узлов и серьёзной нагрузки нужна серверная СУБД.

## Перед запуском

Все следующие команды выполняйте в **корне** существующего репозитория `museum_cicd` на Mac. Файлы этой лабораторной должны уже находиться в нём и быть закоммичены в соответствующей ветке. Не копируйте поверх них старый `Jenkinsfile` лабораторной № 2.

1. Запустите **Docker Desktop** и убедитесь, что `docker info` работает.
2. Установите инструменты, если их ещё нет: `brew install kind kubernetes-cli`. Проверьте `kind version` и `kubectl version --client`.
3. Запустите Jenkins: `brew services start jenkins-lts`; проверьте `http://127.0.0.1:8080`. Jenkins должен работать под тем же пользователем Mac, который запускает Docker Desktop. Если вы запускали Jenkins иначе и он уже работает, оставьте его текущий способ запуска.
4. Оставьте существующий GitHub webhook и ngrok на Jenkins `8080`, если ngrok нужен GitHub для доступа к локальному Mac: `ngrok http 8080`. При смене адреса ngrok обновите URL вебхука GitHub, сохраняя путь `/github-webhook/`. Для локального запуска кластера ngrok не нужен; он нужен только для доставки события GitHub в Jenkins.
5. Один раз выполните `bash scripts/setup-kind.sh`. Скрипт поднимет локальный Registry из прошлой лабораторной (`127.0.0.1:5001`), остановит старые контейнеры сайта Compose, сохранит резервную копию старой базы и создаст кластер `museum-lab3`. Адрес сайта останется `http://127.0.0.1:8081`. Не запускайте прежний `compose.yaml` сайта одновременно с kind: оба занимают порт 8081. Между остановкой прежнего Compose и успешным развёртыванием `main` сайт на 8081 временно недоступен.

Проверьте окружение:

```bash
docker info
kind get clusters
kubectl --context kind-museum-lab3 get nodes
curl -f http://127.0.0.1:5001/v2/
```

Если Docker Hub не отдаёт образ узла kind, это проблема получения образа кластера, а не кода сайта. Сначала проверьте `kind create cluster` и доступ Docker Desktop к источнику образа. Образы Python, nginx и Registry в проекте взяты из `public.ecr.aws`, как в лабораторной № 2.

## Первое развёртывание и ветки

Сохраните изменения в новой ветке `feature/lab3-kubernetes`, отправьте её на GitHub. В существующем Jenkins Multibranch Pipeline `museum-cicd` эта ветка должна пройти тесты, сборку **двух** Docker-образов и публикацию обоих в Registry; стадии Deploy и Health check пропускаются. Затем перенесите изменения в `dev`: там тоже только CI и публикация образов. После проверки перенесите их в `main`: именно сборка `main` применит манифесты к Kubernetes и обновит сайт. Если существующая работа с ветками у вас устроена иначе, сохраняйте этот принцип: публиковать для всех веток, развёртывать только `main`.

Пример для чистого `main`, когда новые файлы уже скопированы в рабочую папку и ещё не закоммичены:

```bash
git switch -c feature/lab3-kubernetes
git add .gitignore Dockerfile Jenkinsfile README.md LAB3_GUIDE.md app services/users k8s nginx/k8s.conf scripts/setup-kind.sh scripts/deploy-k8s.sh
git commit -m "ЛР3: два микросервиса и Kubernetes"
git push -u origin feature/lab3-kubernetes
```

Затем после успешной сборки `feature/lab3-kubernetes`:

```bash
git switch dev
git merge feature/lab3-kubernetes
git push origin dev
git switch main
git merge dev
git push origin main
```

Если Git сообщает о конфликте, не продолжайте пуш вслепую: откройте конфликтующие файлы, объедините изменения и завершите merge коммитом. Jenkins читает `Jenkinsfile` **из каждой ветки**, поэтому он должен быть в каждой из трёх веток. Пользовательские правки страницы, сделанные в вашем репозитории, сохраняйте при разрешении конфликтов.

В `Jenkinsfile` тестируются два бэкенда, собираются и отправляются два образа с тегом `<имя_ветки>-<12_символов_SHA>`. Этап `Deploy to Kubernetes` выполняется только в `main`, применяет `k8s/*.yaml` и ждёт запуска реплик. `Health check` проверяет оба сервиса через nginx. Записи Registry проверяются, например, так:

```bash
curl -s http://127.0.0.1:5001/v2/_catalog
curl -s http://127.0.0.1:5001/v2/museum-core/tags/list
curl -s http://127.0.0.1:5001/v2/museum-users/tags/list
```

**Важно:** в новой ветке Jenkins тоже требует работающий Registry. Если `Check registry` упал с `curl: (7)`, выполните `bash scripts/setup-kind.sh` в папке проекта на Mac и повторите сборку. Для веток `dev`/`feature` кластер при проверке не меняется.

## Как проверить лабораторную

После успешной сборки `main` откройте `http://127.0.0.1:8081`. В меню должна появиться вкладка **Пользователи**; добавьте запись, обновите страницу и убедитесь, что запись осталась. Разделы «Экспонаты» и «Сотрудники» продолжают работать.

```bash
curl -f http://127.0.0.1:8081/health
curl -f http://127.0.0.1:8081/users-health
curl -f http://127.0.0.1:8081/api/users
curl -f http://127.0.0.1:8081/api/exhibits
kubectl --context kind-museum-lab3 -n museum get deployments,replicasets,pods,services,pvc
```

У `museum-core`, `museum-users` и `museum-web` должно быть `2/2` готовых реплик. Для демонстрации восстановления удалите **один Pod users**, затем наблюдайте создание замены:

```bash
kubectl --context kind-museum-lab3 -n museum get pods -l app=museum-users
kubectl --context kind-museum-lab3 -n museum delete pod ИМЯ_ОДНОГО_POD
kubectl --context kind-museum-lab3 -n museum get pods -l app=museum-users -w
```

Замените `ИМЯ_ОДНОГО_POD` точным именем из предыдущей команды. Прервите наблюдение `Ctrl+C`, затем проверьте `kubectl --context kind-museum-lab3 -n museum get deployment museum-users` и вновь откройте вкладку «Пользователи»: данные должны сохраниться. Для демонстрации разделения посмотрите `kubectl --context kind-museum-lab3 -n museum get pods -o wide` и обе базы на Mac: `ls -l "$HOME/museum-deploy/shared/museum.db" "$HOME/museum-deploy/users/users.db"`.

## Если сборка не проходит

| Где ошибка | Что проверить |
| --- | --- |
| `Check registry` | `docker ps`, затем `bash scripts/setup-kind.sh` и `curl -f http://127.0.0.1:5001/v2/` |
| `Build images` | `docker info`, доступ к `public.ecr.aws`; локально `docker build -t museum-test .` и `docker build -f services/users/Dockerfile -t museum-users-test .` |
| `Deploy to Kubernetes` | `kubectl --context kind-museum-lab3 get nodes`, `kubectl --context kind-museum-lab3 -n museum get pods,events` |
| `ImagePullBackOff` | Работает ли Registry; повторите `bash scripts/setup-kind.sh` для подключения Registry к сети kind |
| Не удаётся занять порт 8081 | `lsof -nP -iTCP:8081 -sTCP:LISTEN`; остановите прежний процесс сайта, если это не контейнер из проекта |
| `CrashLoopBackOff` | `kubectl --context kind-museum-lab3 -n museum logs deployment/museum-users` или `deployment/museum-core` |
| Старая страница | Убедитесь, что сборка `main` обновила `museum-core`, и обновите браузер с очисткой кэша |

Чтобы увидеть последние события: `kubectl --context kind-museum-lab3 -n museum get events --sort-by=.lastTimestamp`. Если терминалы и VS Code были закрыты, снова запустите Docker Desktop, Jenkins и при необходимости ngrok. Registry с `restart: unless-stopped` обычно поднимется с Docker Desktop; `bash scripts/setup-kind.sh` безопасно повторно подключит Registry к kind.

## Структура отчёта

1. Цель: разделение музейного приложения на два сервиса, развёртывание в одноузловом Kubernetes и проверка восстановления Pod.
2. Структура: таблица двух сервисов выше, nginx, две SQLite базы; укажите, что пользователи не хранятся в основной базе.
3. Настройка: Docker Desktop, `kind`, `kubectl`, локальный Registry, `setup-kind.sh`; снимок `get nodes`.
4. Конфигурация: `k8s/kind-config.yaml.template`, `storage.yaml`, `services.yaml`, `workloads.yaml.template`, `nginx/k8s.conf`, два Dockerfile и стадии Jenkins; снимки двух образов в Registry и `get deployments,replicasets,pods,pvc`.
5. Проверка: страница музея, вкладка «Пользователи», два health endpoint, успешная сборка `main`, удаление одного Pod и новая реплика; снимки до и после.
6. Вывод: автоматическое восстановление контейнера, отдельные базы и независимые серверные образы; ограничение одного узла и SQLite для промышленной нагрузки.

Не вставляйте в отчёт снимки предполагаемого запуска: сделайте их после реального развёртывания на Mac.
