import uuid
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# =====================
# BASIC TESTS
# =====================

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Project is working 🚀"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# =====================
# HELPER FUNCTIONS
# =====================

def register_user(role="employee"):
    email = f"{role}_{uuid.uuid4().hex[:8]}@test.com"

    response = client.post("/users/register", json={
        "name": f"Test {role}",
        "email": email,
        "password": "123456"
    })

    assert response.status_code == 200

    from app.database import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()

    if role != "employee":
        user.role = role
        db.commit()
        db.refresh(user)

    user_id = user.id
    db.close()

    return email, user_id


def login_and_get_token(email):
    response = client.post("/users/login", data={
        "username": email,
        "password": "123456"
    })

    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def create_admin_headers():
    email, user_id = register_user(role="admin")
    token = login_and_get_token(email)
    return auth_headers(token), user_id


def create_project(headers):
    response = client.post("/projects/", json={
        "name": f"Project {uuid.uuid4().hex[:6]}",
        "description": "Test project"
    }, headers=headers)

    assert response.status_code == 200
    return response.json()


def create_task(headers, project_id, assignee_id):
    response = client.post("/tasks/", json={
        "title": f"Task {uuid.uuid4().hex[:6]}",
        "description": "Test task",
        "priority": "high",
        "project_id": project_id,
        "assignee_id": assignee_id
    }, headers=headers)

    assert response.status_code == 200
    return response.json()


# =====================
# AUTH TESTS
# =====================

def test_register_user():
    email = f"test_{uuid.uuid4().hex[:8]}@test.com"

    response = client.post("/users/register", json={
        "name": "Test User",
        "email": email,
        "password": "123456"
    })

    assert response.status_code == 200
    assert response.json()["email"] == email


def test_login_user():
    email, _ = register_user()

    response = client.post("/users/login", data={
        "username": email,
        "password": "123456"
    })

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_duplicate_email_register():
    email = f"duplicate_{uuid.uuid4().hex[:8]}@test.com"

    response1 = client.post("/users/register", json={
        "name": "User One",
        "email": email,
        "password": "123456"
    })

    response2 = client.post("/users/register", json={
        "name": "User Two",
        "email": email,
        "password": "123456"
    })

    assert response1.status_code == 200
    assert response2.status_code == 400


def test_unauthorized_access_blocked():
    response = client.get("/projects/")
    assert response.status_code in [401, 403]


# =====================
# ROLE TESTS
# =====================

def test_employee_cannot_get_projects():
    email, _ = register_user(role="employee")
    token = login_and_get_token(email)

    response = client.get(
        "/projects/",
        headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_admin_can_get_projects():
    headers, _ = create_admin_headers()

    response = client.get("/projects/", headers=headers)

    assert response.status_code == 200


# =====================
# PROJECT TESTS
# =====================

def test_create_project():
    headers, admin_id = create_admin_headers()

    response = client.post("/projects/", json={
        "name": "Test Project",
        "description": "desc"
    }, headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Test Project"
    assert response.json()["created_by"] == admin_id


def test_update_project():
    headers, _ = create_admin_headers()
    project = create_project(headers)

    response = client.put(f"/projects/{project['id']}", json={
        "name": "Updated Project",
        "description": "Updated description"
    }, headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Project"
    assert response.json()["description"] == "Updated description"


def test_delete_project():
    headers, _ = create_admin_headers()
    project = create_project(headers)

    response = client.delete(
        f"/projects/{project['id']}",
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Project deleted successfully"


def test_project_not_found():
    headers, _ = create_admin_headers()

    response = client.get("/projects/999999", headers=headers)

    assert response.status_code == 404


def test_projects_cache():
    headers, _ = create_admin_headers()

    first_response = client.get("/projects/", headers=headers)
    second_response = client.get("/projects/", headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert isinstance(second_response.json(), list)


# =====================
# TASK TESTS
# =====================

def test_create_task():
    headers, admin_id = create_admin_headers()
    project = create_project(headers)

    task = client.post("/tasks/", json={
        "title": "Task 1",
        "description": "desc",
        "priority": "high",
        "project_id": project["id"],
        "assignee_id": admin_id
    }, headers=headers)

    assert task.status_code == 200
    assert task.json()["title"] == "Task 1"
    assert task.json()["created_by"] == admin_id


def test_update_task():
    headers, admin_id = create_admin_headers()
    project = create_project(headers)
    task = create_task(headers, project["id"], admin_id)

    response = client.put(f"/tasks/{task['id']}", json={
        "title": "Updated Task",
        "description": "Updated task description",
        "priority": "medium",
        "project_id": project["id"],
        "assignee_id": admin_id
    }, headers=headers)

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Task"
    assert response.json()["priority"] == "medium"
    assert response.json()["created_by"] == admin_id


def test_delete_task():
    headers, admin_id = create_admin_headers()
    project = create_project(headers)
    task = create_task(headers, project["id"], admin_id)

    response = client.delete(
        f"/tasks/{task['id']}",
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Task deleted successfully"


def test_task_not_found():
    headers, _ = create_admin_headers()

    response = client.get("/tasks/999999", headers=headers)

    assert response.status_code == 404


def test_filter_tasks_by_status_priority_assignee():
    headers, admin_id = create_admin_headers()
    project = create_project(headers)
    create_task(headers, project["id"], admin_id)

    response = client.get(
        f"/tasks/?status=To Do&priority=high&assignee_id={admin_id}",
        headers=headers
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_tasks_cache():
    headers, _ = create_admin_headers()

    first_response = client.get("/tasks/", headers=headers)
    second_response = client.get("/tasks/", headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert isinstance(second_response.json(), list)


# =====================
# EMPLOYEE PERMISSION TESTS
# =====================

def test_employee_cannot_update_unassigned_task_status():
    admin_headers, admin_id = create_admin_headers()

    employee_email, employee_id = register_user(role="employee")
    employee_token = login_and_get_token(employee_email)
    employee_headers = auth_headers(employee_token)

    project = create_project(admin_headers)
    task = create_task(admin_headers, project["id"], admin_id)

    response = client.put(
        f"/tasks/{task['id']}/status",
        json={"status": "In Progress"},
        headers=employee_headers
    )

    assert response.status_code == 403


# =====================
# WORKFLOW TESTS
# =====================

def test_task_invalid_status_transition():
    headers, admin_id = create_admin_headers()
    project = create_project(headers)
    task = create_task(headers, project["id"], admin_id)

    response = client.put(
        f"/tasks/{task['id']}/status",
        json={"status": "Done"},
        headers=headers
    )

    assert response.status_code == 400


def test_task_valid_status_transition():
    headers, admin_id = create_admin_headers()
    project = create_project(headers)
    task = create_task(headers, project["id"], admin_id)

    response = client.put(
        f"/tasks/{task['id']}/status",
        json={"status": "In Progress"},
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"