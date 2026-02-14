from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, users, classes, exercises, exercise_lists, submissions, grades
from app.config import settings

# Create FastAPI application
app = FastAPI(
    title="Autograder API",
    description="API for automated code grading with sandboxed execution and LLM feedback",
    version="2.0.0",
    debug=settings.debug,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure specific origins in production
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
