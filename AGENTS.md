# AGENTS

## Project Overview

This is a Python application that works as a sidecar to mattcburns/ironic-aio to encapsulate business logic. This API provides a clean interface for managing Ironic operations while keeping business-specific logic separate from the core Ironic infrastructure.

See README.md for development setup and testing commands.

## Development Directives

### Python Dependencies
- **Minimize dependencies**: Only add new Python packages when absolutely necessary
- Prefer standard library solutions over third-party packages when feasible
- **Use simple, well-proven solutions**: Favor mature, widely-adopted libraries over cutting-edge alternatives
- **AGPL v3 Compatibility**: All dependencies MUST be licensed under AGPL v3 compatible licenses (e.g., MIT, Apache 2.0, BSD, LGPL, AGPL)
- Reject dependencies with incompatible licenses (e.g., proprietary, GPL with linking restrictions)
- Every core library used MUST have a justification documented in `README.md`
- Carefully evaluate the trade-offs before introducing new dependencies
- Keep `requirements.txt` lean and well-documented
- A common implementation for both the MCP and REST APIs - all features must be available in both.

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
- Once design documents are written and Implemented they should not be changed. Future design changes should be a new design.

### Branching Strategy
- **Create branches from master**: Always create new branches off of `master`, never create sub-branches of existing feature branches
- **One branch per design**: Each design implementation gets a single dedicated branch
- **BEFORE starting implementation create a branch**
- Branch naming should reference the design number (e.g., `design-001-api-setup`)
- Infrastructure and tooling designs follow the same branching discipline

### CI/CD and Build Automation
- **Python-based build scripts**: Use Python with standard library for build automation instead of bash
- **Design-driven infrastructure**: Build automation and CI/CD workflows MUST be documented as designs in the `designs/` directory
- **GitHub Actions integration**: Automated builds and releases use GitHub Actions workflows
- **Environment parity**: Build scripts must work identically in local development and CI/CD environments
- **Configuration flexibility**: Support both CLI arguments and environment variables for configuration
- **Metadata tracking**: Build processes should generate and save metadata (digests, tags, status) for auditing
- **Container registry agnostic**: Support multiple registries (Docker Hub, GHCR, private registries)
- **Automated releases**: Tag-based releases (v* pattern) trigger automated container builds and pushes

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

### Licensing
- **Project License**: This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0)
- **License Headers**: All new Python source files (.py) MUST include the following AGPL v3 license header at the top:
```python
# Copyright (C) 2026 Matthew Burns
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
- License headers are NOT required for: configuration files, test files, documentation files, or data files
- When adding headers, use the current year and the project owner as the copyright holder

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
