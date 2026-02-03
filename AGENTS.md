# AGENTS

## Project Overview

This is a Python application that works as a sidecar to mattcburns/ironic-aio to encapsulate business logic. This API provides a clean interface for managing Ironic operations while keeping business-specific logic separate from the core Ironic infrastructure.

See README.md for development setup and testing commands.

## Development Directives

### Python Dependencies
- **Minimize dependencies**: Only add new Python packages when absolutely necessary
- Prefer standard library solutions over third-party packages when feasible
- **Use simple, well-proven solutions**: Favor mature, widely-adopted libraries over cutting-edge alternatives
- Every core library used MUST have a justification documented in `README.md`
- Carefully evaluate the trade-offs before introducing new dependencies
- Keep `requirements.txt` lean and well-documented

### API Design
- **OpenAPI Specification**: All API endpoints MUST be defined using OpenAPI (Swagger) specifications
- The OpenAPI spec should be the source of truth for the API contract
- Include comprehensive descriptions, request/response schemas, and examples
- Keep the API RESTful and follow standard HTTP conventions

### Design Documents
- All design documents are stored in `designs/` directory
- **Numbered implementation order**: Designs should be numbered sequentially in the order they should be implemented
- **Keep designs small**: Each design should be scoped small enough for an AI agent to implement without exceeding token limits
- **Two states only**: Designs have only two states - "to be implemented" and "implemented"
- **Complete implementation required**: A design is only complete when ALL components of the design document are implemented
- When implementation is complete, update the design document to mark it as "implemented"
- Breaking large features into multiple small, numbered designs is preferred over single large designs

### Branching Strategy
- **Create branches from master**: Always create new branches off of `master`, never create sub-branches of existing feature branches
- **One branch per design**: Each design implementation gets a single dedicated branch
- Branch naming should reference the design number (e.g., `design-001-api-setup`)

### Testing Requirements
- **All new code MUST include tests**: No code should be merged without corresponding test coverage
- Write unit tests for individual functions and business logic
- Include integration tests for API endpoints
- Aim for high test coverage (minimum 80%)
- Tests should be located in a `tests/` directory
- Use pytest as the testing framework
- **Design completion criteria**: Before marking a design as implemented, ensure:
  - New tests verify all functionality introduced by the design
  - All existing tests continue to pass

### Code Quality
- **Simplicity first**: Write code as simple as possible to enable both AI agents and junior-level engineers to contribute
- Avoid clever or overly complex solutions - prefer explicit, readable code
- Follow PEP 8 style guidelines
- Write clear, self-documenting code with meaningful variable and function names
- Add docstrings to all public functions and classes
- Keep functions small and focused on a single responsibility
- Handle errors gracefully with appropriate exception handling

### Architecture Principles
- Maintain separation of concerns between the API sidecar and Ironic core
- Keep business logic encapsulated within the API layer
- Design for modularity and testability
- Consider scalability and performance in design decisions
- **DRY**: All designs should focus on reducing code duplication and emphasize
  simple modification without requiring tons of context.
