# Музейный архив

Клиент-серверная информационная система для лабораторной работы по CI/CD. Сервер написан на Flask, данные хранятся в SQLite, интерфейс создан на обычных HTML, CSS и JavaScript.

Первая лабораторная разворачивала сайт без Docker через Waitress. Во второй лабораторной Jenkins собирает Docker-образ приложения, а nginx направляет запросы в контейнер Flask/Waitress. База остаётся в `~/museum-deploy/shared/museum.db`.

## Что реализовано

В системе есть пять связанных разделов:

1. Экспонаты.
2. Коллекции.
3. Залы.
4. Сотрудники.
5. События.

Для каждого раздела доступны создание, чтение, изменение и удаление. Проект демонстрирует не менее 20 CRUD-операций: 5 сущностей × 4 операции.

Дополнительно реализованы поиск, статистика, проверка состояния сервера и автоматические тесты API. Экспонаты связаны с коллекциями и залами внешними ключами.

## Структура

```text
museum_cicd/
├── app/
│   ├── static/            # CSS и JavaScript
│   ├── templates/         # HTML-интерфейс
│   ├── __init__.py        # создание Flask-приложения
│   ├── api.py             # REST API и CRUD
│   ├── db.py              # подключение SQLite
│   ├── schema.sql         # структура базы данных
│   └── seed.sql           # демонстрационные данные
├── scripts/
│   ├── deploy.sh          # развёртывание production-версии
│   ├── deploy-container.sh # развёртывание второй лабораторной
│   └── stop.sh            # остановка production-сервера
├── tests/                 # автотесты pytest
├── Jenkinsfile            # CI/CD Pipeline as Code
├── Dockerfile
├── compose.yaml
├── nginx/default.conf     # конфигурация обратного прокси
├── requirements.txt
├── run.py                 # локальный запуск
└── wsgi.py                # production-точка входа
```

## Локальный запуск для разработки

Требуется Python 3.10 или новее.

### macOS или Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Открыть http://127.0.0.1:5050. База `instance/museum.db` создастся автоматически.

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

## Автотесты

```bash
python -m pytest
```

Тесты используют отдельную временную базу и не изменяют рабочие данные.

## Production-запуск без Docker

Сценарий `scripts/deploy.sh` выполняет следующие действия:

1. Копирует текущую версию проекта в `~/museum-deploy/releases/<номер-сборки>`.
2. Создаёт отдельное production-окружение `~/museum-deploy/venv`.
3. Устанавливает зависимости.
4. Сохраняет SQLite-базу вне каталога с кодом в `~/museum-deploy/shared/museum.db`.
5. Останавливает предыдущий процесс Waitress.
6. Переключает ссылку `~/museum-deploy/current` на новую версию.
7. Запускает сайт на http://127.0.0.1:8081.

Ручная проверка развёртывания:

```bash
chmod +x scripts/deploy.sh scripts/stop.sh
BUILD_NUMBER=manual APP_PORT=8081 scripts/deploy.sh
curl http://127.0.0.1:8081/health
```

Остановить production-версию:

```bash
scripts/stop.sh
```

## Production-запуск в контейнерах для лабораторной работы 2

Инструкция по переходу и проверке nginx находится в [LAB2_GUIDE.md](LAB2_GUIDE.md). Инструкция по публикации образов в Docker Registry — в [REGISTRY_GUIDE.md](REGISTRY_GUIDE.md). Потребуется Docker Desktop с Docker Compose. После деплоя сайт доступен по прежнему адресу http://127.0.0.1:8081, но порт обслуживает nginx.

## Логика CI/CD лабораторной работы 2

Для всех веток Jenkins выполняет:

1. Получение кода из GitHub.
2. Проверку Python и Git.
3. Установку зависимостей.
4. Запуск автотестов.
5. Компиляционную проверку Python.
6. Сборку Docker-образа с тегом ветки и коммита и публикацию его в локальном Docker Registry.

Только для `main` дополнительно выполняются:

1. Загрузку опубликованного образа из registry и развёртывание двух контейнеров через `scripts/deploy-container.sh` и Docker Compose.
2. Проверку адреса `/health` через nginx.

Рабочая версия приложения находится в Docker-образе, а конфигурация контейнеров — в `~/museum-deploy/container`. Локальные изменения в редакторе не меняют сайт. Он обновляется после commit, push в GitHub, успешных тестов и выполнения стадии Deploy для ветки `main`.

## API

Для ресурсов `exhibits`, `collections`, `halls`, `employees`, `events` доступны:

| Метод | Адрес | Операция |
|---|---|---|
| GET | `/api/<resource>` | Получить все записи |
| GET | `/api/<resource>/<id>` | Получить одну запись |
| POST | `/api/<resource>` | Создать запись |
| PUT | `/api/<resource>/<id>` | Изменить запись |
| DELETE | `/api/<resource>/<id>` | Удалить запись |

Дополнительные маршруты:

- `GET /api/stats` — статистика;
- `GET /health` — проверка готовности приложения.
