from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services import Grader

app = FastAPI(
    title="Autograder API",
    description="API for grading Python code submissions",
    version="1.0.0",
)


class TestCase(BaseModel):
    input: str
    expected: str


class GradeRequest(BaseModel):
    code: str
    requirements: str
    test_cases: list[TestCase]


class LLMValidation(BaseModel):
    valid: bool
    feedback: str


class TestResultResponse(BaseModel):
    input: str
    expected: str
    actual: str
    passed: bool
    error: str | None = None


class GradeResponse(BaseModel):
    passed: bool
    score: float
    llm_validation: LLMValidation
    test_results: list[TestResultResponse]


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/grade", response_model=GradeResponse)
def grade_submission(request: GradeRequest):
    """
    Grade a Python code submission.

    Validates code using Claude API and executes test cases in a Docker sandbox.
    """
    try:
        grader = Grader()
        result = grader.grade(
            code=request.code,
            requirements=request.requirements,
            test_cases=[tc.model_dump() for tc in request.test_cases],
        )

        return GradeResponse(
            passed=result.passed,
            score=result.score,
            llm_validation=LLMValidation(
                valid=result.llm_validation.valid,
                feedback=result.llm_validation.feedback,
            ),
            test_results=[
                TestResultResponse(
                    input=tr.input,
                    expected=tr.expected,
                    actual=tr.actual,
                    passed=tr.passed,
                    error=tr.error,
                )
                for tr in result.test_results
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
