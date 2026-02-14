import os
from dataclasses import dataclass

from anthropic import Anthropic


@dataclass
class ValidationResult:
    valid: bool
    feedback: str


class LLMValidator:
    def __init__(self, api_key: str | None = None):
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def validate(self, code: str, requirements: str) -> ValidationResult:
        prompt = f"""You are a code reviewer validating Python code against requirements.

Requirements:
{requirements}

Code to validate:
```python
{code}
```

Analyze the code and determine:
1. Is the Python syntax valid?
2. Does the code attempt to fulfill the requirements?
3. Are there any obvious bugs or issues?

Respond in this exact format:
VALID: true or false
FEEDBACK: Your brief feedback here (1-2 sentences)"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text
        lines = response_text.strip().split("\n")

        valid = False
        feedback = "Unable to parse validation response"

        for line in lines:
            if line.startswith("VALID:"):
                valid = "true" in line.lower()
            elif line.startswith("FEEDBACK:"):
                feedback = line.replace("FEEDBACK:", "").strip()

        return ValidationResult(valid=valid, feedback=feedback)
