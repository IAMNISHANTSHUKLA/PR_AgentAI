# Code Quality & Style Standards

## General Principles
- Follow PEP 8 for Python code style.
- Maximum line length: 100 characters.
- Use 4 spaces for indentation, never tabs.
- All public functions and classes MUST have docstrings (Google style).
- Use type hints for all function signatures.

## Naming Conventions
- Classes: PascalCase (e.g., `UserService`, `PaymentGateway`)
- Functions/methods: snake_case (e.g., `get_user_by_id`, `process_payment`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`)
- Private methods: prefix with underscore (e.g., `_validate_input`)
- Boolean variables: prefix with is/has/should (e.g., `is_active`, `has_permission`)

## Error Handling
- Use specific exception types, never bare `except:` clauses.
- Create custom exception classes for domain-specific errors.
- Always include contextual information in error messages.
- Use `logging` module, never `print()` statements in production code.

## Testing
- All new features must include unit tests with >= 80% coverage.
- Test both happy path and error cases.
- Use pytest as the testing framework.
- Mock external dependencies in unit tests.
- Integration tests should use test databases, never production data.

## Design Patterns
- Follow SOLID principles.
- Prefer composition over inheritance.
- Use dependency injection for testability.
- Keep functions under 30 lines where possible.
- Cyclomatic complexity should not exceed 10 per function.

## Git Workflow
- Branch names: feature/, bugfix/, hotfix/ prefixes.
- Commit messages: conventional commits format (feat:, fix:, docs:, refactor:).
- PRs must be reviewed by at least one team member.
- Squash merge to keep history clean.
