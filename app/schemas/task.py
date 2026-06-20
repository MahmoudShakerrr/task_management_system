from enum import Enum
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskStatus(str, Enum):
    todo = "To Do"
    in_progress = "In Progress"
    done = "Done"


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.medium


class TaskCreate(TaskBase):
    project_id: int
    assignee_id: int


class TaskResponse(TaskBase):
    id: int
    status: str
    project_id: int
    assignee_id: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskUpdate(BaseModel):
    title: str
    description: str | None = None
    priority: TaskPriority
    project_id: int
    assignee_id: int