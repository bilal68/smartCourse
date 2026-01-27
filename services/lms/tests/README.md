# Test Suite

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific module
pytest tests/modules/enrollments/

# Run specific layer
pytest tests/modules/enrollments/test_routes.py
pytest tests/modules/enrollments/test_service.py

# Run specific test class
pytest tests/modules/enrollments/test_routes.py::TestEnrollmentAuthPermissions

# Run specific test
pytest tests/modules/enrollments/test_service.py::TestEnrollmentPrerequisites::test_enroll_without_prerequisites_succeeds

# Run tests matching pattern
pytest -k "prerequisite"

# Show print statements
pytest -s
```

## Test Structure (Modular - Mirrors App Architecture) ✅ 64 Tests Passing

```
tests/
├── conftest.py                          # Global fixtures
└── modules/                             # Mirrors app/modules/
    ├── enrollments/                     # Mirrors app/modules/enrollments/
    │   ├── test_routes.py               # 20 tests - API endpoints (auth, CRUD, validation)
    │   └── test_service.py              # 10 tests - Business logic (prerequisites, limits)
    └── courses/                         # Mirrors app/modules/courses/
        ├── test_routes.py               # 5 tests - Prerequisite management API
        └── test_service.py              # 29 tests - Business logic (CRUD, auth, publish, prerequisites)
```

**Benefits of this architecture:**
- ✅ **Layer-based** - Maps to actual code files (routes.py, service.py)
- ✅ **No redundancy** - Folder already says "enrollments"
- ✅ **Scales perfectly** - Add test_repository.py, test_models.py as needed
- ✅ **Clear scope** - Know exactly which layer is tested
- ✅ **Mirrors app** - Easy navigation between app code and tests

## Test Coverage by Layer

| Module | Layer | Tests | Coverage | Details |
|--------|-------|-------|----------|---------|
| **enrollments** | routes.py | 20 | 82% | Auth/permissions, CRUD operations, validation, error handling |
| **enrollments** | service.py | 10 | 96% | Prerequisites validation, enrollment limits, archived courses |
| **enrollments** | repository.py | - | 98% | (tested indirectly) |
| **courses** | routes.py | 5 | 66% | Add/remove/list prerequisites (instructor only) |
| **courses** | service.py | 29 | 98% | Creation, retrieval, update, delete, publish, prerequisites |
| **courses** | repository.py | - | 63% | (tested indirectly) |
| **Overall** | - | **64** | **70%** | All tests passing |

**Future additions:**
- `test_repository.py` - Data access layer tests
- `test_models.py` - Model validation tests
- `conftest.py` (per module) - Module-specific fixtures

## Writing New Tests

1. Use fixtures from `conftest.py` for common setup
2. Follow naming convention: `test_<feature>_<expected_outcome>`
3. Use descriptive docstrings
4. Assert specific error messages, not just status codes
