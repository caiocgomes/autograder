from dataclasses import dataclass

from .llm_validator import LLMValidator, ValidationResult
from .sandbox import Sandbox, ExecutionResult


@dataclass
class TestResult:
    input: str
    expected: str
    actual: str
    passed: bool
    error: str | None = None


@dataclass
class GradeResult:
    passed: bool
    score: float
    llm_validation: ValidationResult
    test_results: list[TestResult]


class Grader:
    def __init__(self, api_key: str | None = None):
        self.validator = LLMValidator(api_key=api_key)
        self.sandbox = Sandbox()

    def grade(
        self,
        code: str,
        requirements: str,
        test_cases: list[dict],
    ) -> GradeResult:
        validation = self.validator.validate(code, requirements)

        test_results: list[TestResult] = []

        if not validation.valid:
            for tc in test_cases:
                test_results.append(
                    TestResult(
                        input=tc["input"],
                        expected=tc["expected"],
                        actual="",
                        passed=False,
                        error="Code validation failed",
                    )
                )
            return GradeResult(
                passed=False,
                score=0.0,
                llm_validation=validation,
                test_results=test_results,
            )

        for tc in test_cases:
            exec_result: ExecutionResult = self.sandbox.execute(code, tc["input"])

            if exec_result.error:
                test_results.append(
                    TestResult(
                        input=tc["input"],
                        expected=tc["expected"],
                        actual="",
                        passed=False,
                        error=exec_result.error,
                    )
                )
            else:
                actual = exec_result.output
                passed = actual == tc["expected"]
                test_results.append(
                    TestResult(
                        input=tc["input"],
                        expected=tc["expected"],
                        actual=actual,
                        passed=passed,
                    )
                )

        passed_count = sum(1 for tr in test_results if tr.passed)
        total_count = len(test_results)
        score = (passed_count / total_count * 100) if total_count > 0 else 0.0

        all_passed = all(tr.passed for tr in test_results)

        return GradeResult(
            passed=all_passed,
            score=score,
            llm_validation=validation,
            test_results=test_results,
        )
