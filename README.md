# Lab 7 — SQLAlchemy и Alembic

Продолжение [course-catalog-api](https://github.com/yertayAmantay/course-catalog-api) для Python 3.11+. Схема и точные начальные данные взяты из [course-catalog-db](https://github.com/yertayAmantay/course-catalog-db). На момент работы API в main содержал Lab 4; недостающие маршруты лайков и записей добавлены в рамках перехода к Lab 7. Поиск по названию `q` и валидация параметров сохранены.

## Запуск с нуля

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Windows: Copy-Item .env.example .env
docker compose up -d --wait
alembic upgrade head
# PostgreSQL CLI внутри контейнера:
docker compose exec -T db psql -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 < seed.sql
python check_db.py
python check_models.py
alembic check
fastapi dev main.py
```

Для PowerShell вместо перенаправления: `Get-Content seed.sql | docker compose exec -T db psql -U catalog_app -d course_catalog -v ON_ERROR_STOP=1`.
Swagger: http://localhost:8000/docs. Во втором терминале с активным venv: `python try_errors.py` — должно быть `5 of 5 as expected`.

Если PostgreSQL уже установлен, Docker не нужен. Создать роль и БД через `psql -U postgres`:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
```

Затем `alembic upgrade head` и `psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql`. Файл seed.sql очищает учебные таблицы и сбрасывает ID. Не запускать на рабочих данных. `.env` исключён из Git; в `.env.example` только учебный пароль. Для SQL-лога добавить `SQL_ECHO=true` в локальный `.env`.

## Что изменилось в API

Данные хранятся в PostgreSQL и сохраняются после перезапуска. JSON использует camelCase. Запись на курс теперь принимает `studentId`, а не `studentName`; сначала создаётся студент. Фронтенд прошлой лабораторной потребует изменения контракта.

| Метод | Путь | Поведение |
|---|---|---|
| GET | / | Состояние API |
| GET | /courses | Фильтры is_elective, level; поиск q; sort=popular/title; page, page_size |
| GET | /courses/{id} | Курс либо 404 |
| POST | /courses/{id}/like | Атомарное увеличение likes |
| POST | /students | Создание, 201; занятый email — 409 |
| POST | /enrollments | courseId + studentId; 201, 409 при повторе, 404 для отсутствующей ссылки |
| GET | /enrollments | JOIN с названием курса и именем студента |
| GET | /stats/courses | LEFT JOIN; количество записей, включая ноль |

Пример запроса студента: `{"name":"Nurlan Abenov","email":"nurlan@example.com"}`. Затем `{"courseId":"web-security","studentId":4}` в /enrollments. Номер студента брать из ответа, он не гарантированно равен 4.

## Миграции

| Команда | Назначение |
|---|---|
| alembic upgrade head | Применить все миграции |
| alembic downgrade -1 | Откатить последнюю |
| alembic current | Текущая версия БД |
| alembic history | История |
| alembic heads | Вершины графа |
| alembic check | Найти расхождения моделей и БД |
| alembic revision --autogenerate -m "description" | Создать черновик изменения |
| alembic upgrade 0001:0002 --sql | Посмотреть SQL без выполнения |
| alembic stamp 0001 | Только записать версию существующей схемы |

0001 создаёт три таблицы, ограничения и индекс. 0002 добавляет level в три шага: nullable-колонка → UPDATE существующих строк → NOT NULL. У elective уровень beginner, у остальных intermediate. Постоянного DEFAULT нет.

Для уже существующей схемы Lab 6 сначала сравнить её с 0001, затем `alembic stamp 0001`, затем `alembic upgrade head` и `alembic check`. Нельзя stamp head на схеме без level: это пропустит 0002. Проверка Alembic не покрывает все свойства, в частности CHECK: их надо сверять отдельно.

Самопроверка выполнена на PostgreSQL 17: upgrade → seed → downgrade 0001 → upgrade head → check, затем полный downgrade base → upgrade head → seed → check. После отката 0002 level удаляется вместе со значениями; повторное применение заполняет по правилу, пользовательские значения не восстанавливает.

## Журнал экспериментов

Эксперименты выполнены на отдельном учебном PostgreSQL. Полный вывод команд — verification.txt. В эксперименте 2 входная Pydantic-валидация обойдена через model_construct, затем вызван обработчик: это воспроизводит удаление Field(min_length=2), не меняя итоговую схему.

| № | Что сломано | Наблюдение | Причина | Исправление |
|---|---|---|---|---|
| 1 | uq = table_column_unique | alembic check предлагает удалить старые и добавить новые UNIQUE | Имена метаданных отличаются от реальных | Вернуть column_0_N_name + _key |
| 2 | Пропущена проверка длины имени Pydantic | IntegrityError, students_name_check; необработанная ошибка даёт 500 | CHECK защищает БД, но неизвестен словарю HTTP-ошибок | Вернуть min_length=2, клиент получает 422 |
| 3 | Удалён правильный ключ students_email_key | Повторный email возвращает HTTP 500 | Реальное имя ограничения не найдено в словаре | Вернуть ключ; HTTP 409 |
| 4 | У title снят NOT NULL, затем тип изменён на varchar(100) | check обнаруживает modify_nullable, затем modify_type | Ручной DDL расходится с моделью | SET NOT NULL, TYPE text; check чистый |
| 5 | 0002 сразу добавляет level NOT NULL при наличии строк | contains null values; версия остаётся 0001 | Старым строкам неоткуда получить значение | Три шага: add nullable, backfill, set not null |
| 6 | Убран import models из env.py | autogenerate предлагает drop_table всех трёх таблиц | Base.metadata пустая | Не применять черновик, удалить его и вернуть импорт |
| 7 | В Student добавлено phone без миграции | check обнаруживает add_column students.phone | Модель опередила схему | Удалить экспериментальное поле; в реальной задаче создать миграцию |
| 8 | Две миграции с родителем 0002 | Две heads, upgrade head отказывается работать | Неоднозначная вершина графа | merge heads создаёт 0005 с двумя родителями; после опыта файлы 0003–0005 удалены |

Дополнительно проверены фильтры, пагинация, camelCase, 404, атомарный лайк, создание студента и записи, JOIN, нули в статистике и все пять ошибочных запросов. После экспериментов восстановлены модели, схема и исходные 6/3/6 строк.

## Решения

- SQLAlchemy 2.1, синхронные Session и psycopg 3. Отдельная сессия на запрос закрывается dependency; после IntegrityError явно rollback.
- Pydantic отвечает за JSON и раннюю проверку, SQLAlchemy — за таблицы. CHECK/UNIQUE/FK защищают данные независимо от API.
- Имена ограничений соответствуют PostgreSQL; ответы выбираются по diag.constraint_name, а не по локализованному сообщению. Неизвестная ошибка пробрасывается.
- Лайк выполняет UPDATE likes = likes + 1 RETURNING: параллельные запросы не теряют увеличение счётчика.
- count(Enrollment.id), а не count(*): LEFT JOIN создаёт пустую строку для курса без записей, и count(*) ошибочно даёт 1.
- str → TEXT, datetime → TIMESTAMPTZ; ID — BIGINT GENERATED ALWAYS AS IDENTITY; enrolled_at задаёт сервер.
- passive_deletes=True позволяет БД обрабатывать незагруженные связи по CASCADE/RESTRICT. Загруженные коллекции требуют отдельного учёта при добавлении будущих delete-маршрутов.
- op.f фиксирует конечные имена ограничений, чтобы naming_convention не применялась повторно. Миграции содержат собственное описание схемы, не импортируют текущие модели.
- Дополнительно ограничены page >= 1 и page_size от 1 до 100; сортировка имеет стабильный второй ключ id.

## Сдача

Изменения подготовлены в ветке `lab7-sqlalchemy-alembic` поверх истории исходного API. Есть девять содержательных коммитов Lab 7. Репозитории БД и фронтенда не изменяются. Включён verification.txt с фактическими результатами проверок, включая переход с существующей схемы Lab 6 через stamp 0001, upgrade head и проверку сохранности данных.

Проверенные версии окружения перечислены в requirements-lock.txt. Бонусные задания необязательны и в эту реализацию не включены.
