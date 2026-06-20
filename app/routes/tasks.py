from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import require_project_manager_or_admin, get_current_user, require_admin
from app.dependencies import get_db
from app.models.task import Task
from app.models.user import User
from app.models.project import Project
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate, TaskUpdate
from app.core.logger import logger
from app.core.cache import get_cache, set_cache, delete_cache, delete_cache_pattern

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_manager_or_admin)
):
    project = db.query(Project).filter(Project.id == task.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    assignee = db.query(User).filter(User.id == task.assignee_id).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")

    new_task = Task(
        title=task.title,
        description=task.description,
        priority=task.priority.value if hasattr(task.priority, "value") else task.priority,
        project_id=task.project_id,
        assignee_id=task.assignee_id,
        created_by=current_user.id
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    delete_cache_pattern("tasks*")

    logger.info(
        f"Task created - ID: {new_task.id}, by user: {current_user.id}"
    )

    return new_task


@router.get("/", response_model=list[TaskResponse])
def get_tasks(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_manager_or_admin)
):
    cache_key = f"tasks:status={status}:priority={priority}:assignee={assignee_id}"

    cached_tasks = get_cache(cache_key)

    if cached_tasks:
        print("Tasks From Cache")
        return cached_tasks

    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)

    if priority:
        query = query.filter(Task.priority == priority)

    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)

    tasks = query.all()

    result = []
    for task_item in tasks:
        result.append({
            "id": task_item.id,
            "title": task_item.title,
            "description": task_item.description,
            "status": task_item.status,
            "priority": task_item.priority,
            "project_id": task_item.project_id,
            "assignee_id": task_item.assignee_id,
            "created_by": task_item.created_by,
            "created_at": task_item.created_at
        })

    set_cache(cache_key, result, expire=60)

    print("Tasks From DB")

    return result


@router.get("/{task_id}", response_model=TaskResponse)
def get_task_by_id(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role == "employee" and task.assignee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    if current_user.role not in ["admin", "project_manager", "employee"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    cache_key = f"task:{task_id}:user:{current_user.id}:role:{current_user.role}"

    cached_task = get_cache(cache_key)
    if cached_task:
        print("Task From Cache")
        return cached_task

    result = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "project_id": task.project_id,
        "assignee_id": task.assignee_id,
        "created_by": task.created_by,
        "created_at": task.created_at,
    }

    set_cache(cache_key, result, 60)
    print("Task From DB")

    return result


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_project_manager_or_admin)
):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = db.query(Project).filter(Project.id == task_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    assignee = db.query(User).filter(User.id == task_data.assignee_id).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")

    task.title = task_data.title
    task.description = task_data.description
    task.priority = task_data.priority.value if hasattr(task_data.priority, "value") else task_data.priority
    task.project_id = task_data.project_id
    task.assignee_id = task_data.assignee_id

    db.commit()
    db.refresh(task)

    delete_cache_pattern("tasks*")
    delete_cache(f"task:{task_id}")

    logger.info(
        f"Task updated - ID: {task.id}, by user: {current_user.id}"
    )

    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    delete_cache_pattern("tasks*")
    delete_cache(f"task:{task_id}")

    logger.info(
        f"Task deleted - ID: {task_id}, by user: {current_user.id}"
    )

    return {"message": "Task deleted successfully"}


@router.put("/{task_id}/status", response_model=TaskResponse)
def update_task_status(
    task_id: int,
    status_data: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role == "employee" and task.assignee_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update tasks assigned to you"
        )

    if current_user.role not in ["admin", "project_manager", "employee"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    valid_transitions = {
        "To Do": ["In Progress"],
        "In Progress": ["Done"],
        "Done": []
    }

    current_status = task.status
    new_status = status_data.status.value if hasattr(status_data.status, "value") else status_data.status

    if current_status not in valid_transitions:
        raise HTTPException(status_code=400, detail="Invalid current task status")

    if new_status not in valid_transitions[current_status]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from {current_status} to {new_status}"
        )

    task.status = new_status

    db.commit()
    db.refresh(task)

    delete_cache_pattern("tasks*")
    delete_cache(f"task:{task_id}")

    logger.info(
        f"Task status updated - Task ID: {task.id}, From: {current_status}, To: {new_status}, Updated by User ID: {current_user.id}"
    )

    return task