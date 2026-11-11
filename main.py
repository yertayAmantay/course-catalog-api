from typing import Annotated, Literal
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from db import get_db
from models import Course
from schemas import CourseOut

app = FastAPI(title="Course Catalog API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])
SessionDep = Annotated[Session, Depends(get_db)]
def pagination(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return {"offset": (page - 1) * page_size, "limit": page_size}

@app.get("/")
def read_root():
    return {"message": "Course Catalog API is running"}

@app.get("/courses", response_model=list[CourseOut])
def list_courses(db: SessionDep, is_elective: bool | None = None,
                 sort: Literal["popular", "title"] = "popular", q: str | None = None, p: dict = Depends(pagination)):
    stmt = select(Course)
    if is_elective is not None:
        stmt = stmt.where(Course.is_elective == is_elective)
    if q:
        stmt = stmt.where(Course.title.icontains(q, autoescape=True))
    stmt = stmt.order_by(Course.title, Course.id) if sort == "title" else stmt.order_by(Course.likes.desc(), Course.id)
    return db.scalars(stmt.limit(p["limit"]).offset(p["offset"])).all()

@app.get("/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: str, db: SessionDep):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "Course not found")
    return course

@app.post("/courses/{course_id}/like", response_model=CourseOut)
def like_course(course_id: str, db: SessionDep):
    stmt = update(Course).where(Course.id == course_id).values(likes=Course.likes + 1).returning(Course)
    course = db.scalars(stmt).one_or_none()
    if course is None:
        raise HTTPException(404, "Course not found")
    db.commit()
    return course

