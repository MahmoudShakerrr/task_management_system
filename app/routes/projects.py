from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.dependencies import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.models.task import Task
from app.core.security import get_current_user, require_project_manager_or_admin, require_admin
from app.core.cache import get_cache, set_cache, delete_cache
from app.core.logger import logger

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_manager_or_admin)
):
    new_project = Project(
        name=project.name,
        description=project.description,
        created_by=current_user.id
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    delete_cache("projects")

    logger.info(
        f"Project created - ID: {new_project.id}, by user: {current_user.id}"
    )

    return new_project


@router.get("/", response_model=list[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_manager_or_admin)
):
    cached_projects = get_cache("projects")

    if cached_projects:
        print("From Cache")
        return cached_projects

    projects = db.query(Project).all()

    result = []
    for project in projects:
        result.append({
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "created_by": project.created_by,
            "created_at": project.created_at
        })

    set_cache("projects", result, expire=60)

    print("From DB")

    return result


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_by_id(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role == "employee":
        task = db.query(Task).filter(
            Task.project_id == project_id,
            Task.assignee_id == current_user.id
        ).first()

        if not task:
            raise HTTPException(status_code=403, detail="Not allowed")

    elif current_user.role not in ["admin", "project_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    cache_key = f"project:{project_id}:user:{current_user.id}:role:{current_user.role}"

    cached_project = get_cache(cache_key)
    if cached_project:
        print("Project From Cache")
        return cached_project

    result = {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_by": project.created_by,
        "created_at": project.created_at,
    }

    set_cache(cache_key, result, 60)
    print("Project From DB")

    return result


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_manager_or_admin)
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.name = project_data.name
    project.description = project_data.description

    db.commit()
    db.refresh(project)

    delete_cache("projects")
    delete_cache(f"project:{project_id}")

    logger.info(
        f"Project updated - ID: {project.id}, by user: {current_user.id}"
    )

    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    delete_cache("projects")
    delete_cache(f"project:{project_id}")

    logger.info(
        f"Project deleted - ID: {project_id}, by user: {current_user.id}"
    )

    return {"message": "Project deleted successfully"}