# API Standards

# REST Principles

Use RESTful conventions.

Good:

```text
/api/users/
/api/diaries/
```

Bad:

```text
/api/getUser/
/api/createDiary/
```

---

# HTTP Methods

| Method | Usage |
|---|---|
| GET | Retrieve |
| POST | Create |
| PUT | Full update |
| PATCH | Partial update |
| DELETE | Delete |

---

# Response Standards

## Success

```json
{
  "id": 1,
  "name": "Chicken Breast"
}
```

---

## Validation Error

```json
{
  "errors": {
    "field": ["This field is required."]
  }
}
```

---

# View Rules

Views should:

- validate requests
- call services
- return responses

Views should NOT:

- contain business logic
- perform complex queries
- orchestrate workflows

---

# Serializer Rules

Serializers are only for:

- validation
- serialization
- lightweight transformation

Avoid business workflows in serializers.

---

# API Performance Rules

Always consider:

- select_related
- prefetch_related
- pagination
- N+1 prevention
- query optimization
