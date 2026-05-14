# Django Architecture Standards

# Core Principles

| Layer | Responsibility |
|---|---|
| views | HTTP handling |
| serializers | validation |
| services | business logic |
| selectors | query logic |
| models | data structure |
| permissions | authorization |

---

# Thin View Principle

Views should only:

- parse requests
- authenticate users
- coordinate serializers
- call services
- return responses

---

# Service-Centric Design

Business logic belongs in services.

Benefits:

- reusable workflows
- easier testing
- maintainable architecture
- cleaner views

---

# Selector Pattern

Selectors centralize reusable read queries.

Example:

```python
def get_user_diaries(user_id):
    return (
        DiaryEntry.objects
        .filter(user_id=user_id)
        .select_related("user")
    )
```

---

# Recommended Structure

```text
apps/
    users/
    nutrition/
    diary/
    ai_analysis/
```

Inside each app:

```text
models/
serializers/
views/
services/
selectors/
permissions/
tests/
```

---

# Query Optimization

Always consider:

- N+1 prevention
- select_related
- prefetch_related
- pagination
- indexing

Avoid database access inside loops.

---

# Testing Strategy

Recommended:

```text
tests/
    test_services.py
    test_selectors.py
    test_views.py
```

Priority:

1. services
2. permissions
3. API flows
4. edge cases

---

# Engineering Philosophy

Good backend architecture should be:

- explicit
- maintainable
- scalable
- testable
- understandable

The goal is sustainable backend engineering.
