from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select
import models
from db import Base, SessionLocal, engine
with engine.connect() as connection:
    differences = compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata)
    assert not differences, differences
    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        print(table.name, [(c["name"], str(c["type"]), c["nullable"]) for c in inspector.get_columns(table.name)])
with SessionLocal() as session:
    for model in (models.Course, models.Student, models.Enrollment):
        print(model.__name__, len(session.scalars(select(model)).all()))
print("Models match the database (CHECK constraints require manual review).")
