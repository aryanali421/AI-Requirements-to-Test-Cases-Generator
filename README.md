# TestForge – Requirements-to-Test-Case Generator

**Turn requirements into testable reality.**

TestForge helps translate software requirements into structured test cases. It is designed to identify normal scenarios, boundary conditions, and invalid-input cases so teams can build a stronger testing foundation.

## Core workflow

1. **Project configuration** – Enter details about the application being tested.
2. **Requirements analysis** – Paste functional and non-functional requirements, upload an existing specification, or combine both.
3. **Generation settings** – Select the types of scenarios to explore:
   - **Normal testing:** Verify expected behavior with valid inputs.
   - **Boundary testing:** Explore minimums, maximums, and edge values.
   - **Invalid-input testing:** Check missing, malformed, and unacceptable inputs.
4. **Review test cases** – Inspect the generated scenarios and validate them before execution.

## Supported input formats

- PDF
- DOCX
- TXT

The interface description lists a maximum file size of 200 MB per file. Confirm that the deployed app's upload configuration and hosting limits support this size.

## AI processing

Requirements are analyzed by Groq. Generation depth influences the level of detail in the output; it does not guarantee a particular number of test cases.

## Important notes

- Generated test cases are starting points and should be reviewed against the actual application and acceptance criteria.
- Check that expected results are precise, observable, and testable.
- Add project-specific security, performance, accessibility, and compatibility scenarios where relevant.

## Technology

- Groq for AI-powered requirements analysis and test-case generation.

Update this section with the exact framework, model identifier, and dependencies used by the implementation.

## Author

Aryan Ali
