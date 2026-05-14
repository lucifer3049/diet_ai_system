# Service Layer Standards

# Purpose

The service layer centralizes:

- business logic
- workflows
- orchestration
- external integrations

---

# Responsibilities

Services should handle:

- multi-model workflows
- transaction management
- AI integrations
- reusable business behavior

---

# Services Should NOT

- return DRF Response objects
- contain serializer validation
- depend heavily on request objects

---

# Structure

```text
services/
    diary_service.py
    nutrition_service.py
    ai_analysis_service.py
```

---

# Transaction Example

```python
@transaction.atomic
def create_diary_entry(...):
    ...
```

---

# Selector Usage

Bad:

```python
DiaryEntry.objects.filter(...)
```

repeated everywhere.

Preferred:

```python
entries = diary_selectors.get_user_entries(...)
```

---

# Return Standards

Prefer:

- dataclasses
- typed objects
- explicit result structures

Avoid random mixed dictionaries.

---

# Service Philosophy

A good service layer:

- keeps views thin
- centralizes business logic
- improves maintainability
- improves testability
