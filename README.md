# Course Catalog API

Бэкенд каталога курсов на FastAPI + Pydantic (Advanced Web Technologies, лабораторная 4). Данные — те же шесть курсов, что в `lib/courses.tsx` фронтенда.

## Как запустить

```bash
python3 -m venv .venv            # Windows: python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
fastapi dev main.py
```

Сервер: http://127.0.0.1:8000, документация: `/docs` (Swagger), `/redoc`, схема: `/openapi.json`.

## Маршруты

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/` | проверка, что сервер жив |
| GET | `/courses` | список: `is_elective`, `sort` (`popular` \| `title`), `q`, `page`, `page_size` |
| GET | `/courses/{course_id}` | один курс или 404 |

Пагинация вынесена в зависимость `pagination` и подключена через `Depends`.
В JSON поле называется `is_elective` (snake_case) — согласование с `isElective` фронтенда будет в Lab 5.

## Что было проверено

| Запрос | Результат |
| --- | --- |
| `/courses` | 6 курсов; первый `ai-integration` (32 лайка), последний `api-design` (11) |
| `/courses?is_elective=true` | 2: `ai-integration`, `api-design` |
| `/courses?is_elective=false` | 4: `modern-frontend`, `web-security`, `backend-fastapi`, `databases-postgresql` |
| `/courses?sort=title` | 6 по алфавиту: `ai-integration`, `api-design`, `backend-fastapi`, `modern-frontend`, `databases-postgresql`, `web-security` |
| `/courses?page=1&page_size=2` | `ai-integration`, `modern-frontend` |
| `/courses?page=2&page_size=2` | `web-security`, `backend-fastapi` |
| `/courses?page=3&page_size=2` | `databases-postgresql`, `api-design` |
| `/courses?page=4&page_size=2` | `[]` |
| `/courses/web-security` | 200, один курс |
| `/courses/nope` | 404, `{"detail": "Course not found"}` |
| `/courses?q=react` | `modern-frontend` |
| `/courses?q=api` | `backend-fastapi`, `api-design` |
| `/courses?sort=banana`, `?page=0`, `?page_size=1000` | 422 (бонусная валидация) |
