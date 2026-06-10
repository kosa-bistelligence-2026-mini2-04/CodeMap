"""Services layer — business logic.

Services orchestrate business operations, using repositories for data access
and raising domain exceptions for error handling.

NOTE: this package intentionally does NOT eagerly import service classes.
Doing so caused a circular import via `app.core.config` (which imports
`app.services.rag.config` for forward-reference rebuild) ↔ services that
import `settings` at module level. Import service classes from their
modules directly: `from app.services.user import UserService`.
"""
