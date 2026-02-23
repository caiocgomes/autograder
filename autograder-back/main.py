import logging
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.routers import auth, users, classes, exercises, exercise_lists, submissions, grades
from app.routers import webhooks, products, admin_events, messaging, admin_templates, onboarding, admin_settings
from app.config import settings


# Configure logging
if settings.log_format == "json":
    import json as json_mod

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "request_id": getattr(record, "request_id", None),
            }
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            return json_mod.dumps(log_data)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.root.handlers = [handler]

logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger("autograder")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

# Create FastAPI application
app = FastAPI(
    title="Autograder API",
    description="API for automated code grading with sandboxed execution and LLM feedback",
    version="2.0.0",
    debug=settings.debug,
)

# Configure CORS
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(classes.router)
app.include_router(exercises.router)
app.include_router(exercise_lists.router)
app.include_router(submissions.router)
app.include_router(grades.router)
app.include_router(webhooks.router)
app.include_router(products.router)
app.include_router(admin_events.router)
app.include_router(messaging.router)
app.include_router(admin_templates.router)
app.include_router(onboarding.router)
app.include_router(admin_settings.router)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "2.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
