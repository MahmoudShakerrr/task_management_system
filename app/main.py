from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
from app.database import Base, engine
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.routes.users import router as users_router
from app.routes.projects import router as projects_router
from app.routes.tasks import router as tasks_router
from app.core.logger import logger
from app.core.monitoring import log_request, get_monitoring, reset_monitoring


app = FastAPI(title="Task Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(users_router)
app.include_router(projects_router)
app.include_router(tasks_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        log_request(
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=round(process_time, 4)
        )

        logger.info(
            f"Request completed | Method: {request.method} | "
            f"Endpoint: {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Response Time: {process_time:.4f}s"
        )

        if response.status_code >= 400:
            logger.warning(
                f"Request error | Method: {request.method} | "
                f"Endpoint: {request.url.path} | "
                f"Status: {response.status_code}"
            )

        return response

    except Exception as e:
        process_time = time.time() - start_time

        log_request(
            endpoint=request.url.path,
            status_code=500,
            duration=round(process_time, 4)
        )

        logger.error(
            f"Unhandled exception | Method: {request.method} | "
            f"Endpoint: {request.url.path} | "
            f"Error: {str(e)}",
            exc_info=True
        )

        raise


@app.get("/")
def root():
    return {"message": "Project is working 🚀"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "Task Management System is running"
    }


@app.get("/monitoring")
def monitoring_dashboard():
    return get_monitoring()


@app.delete("/monitoring/reset")
def reset_monitoring_dashboard():
    reset_monitoring()
    return {"message": "Monitoring dashboard reset successfully"}