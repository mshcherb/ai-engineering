# AI Engineering — workspace

Рабочее окружение для курса AI Engineering.

## Быстрый старт

```bash
# поднять контейнер с Python 3.12 + зависимостями курса
docker compose up -d --build

# войти в shell контейнера
docker compose exec python bash

# проверить Python
python --version
```

## FastAPI (когда появится сервис)

```bash
docker compose exec python fastapi dev main.py --host 0.0.0.0 --port 8000
# docs: http://localhost:8000/docs
```

## Полезные команды

```bash
docker compose logs -f python
docker compose down
docker compose exec python pip list
```
