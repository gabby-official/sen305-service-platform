# Lab 3 In Lab Exercise Evidence
GROUP18
GROUP LEADER:OLOWO MORENIKEJI
**Course:** SEN305 | **Project:** VUA ServiceDesk | **Date:** 16 November 2026
**Data safety:** only synthetic laboratory data was used.

## 1. Migration 0002

- File: `backend/requests_app/migrations/0002_service_level_and_resolution.py`
- `0001_initial.py` was not modified.
- Created with: `python manage.py makemigrations requests_app -n service_level_and_resolution`

Operations reported by Django:

```
+ Add field due_at to servicerequest
+ Add field resolution_summary to servicerequest
+ Create index req_status_due_idx on field(s) status, due_at of model servicerequest
```

SQL reviewed with `sqlmigrate` before applying (saved in `docs/sqlmigrate-0002.sql`):

```sql
ALTER TABLE `requests_app_servicerequest` ADD COLUMN `due_at` datetime(6) NULL;
ALTER TABLE `requests_app_servicerequest` ADD COLUMN `resolution_summary` longtext NOT NULL;
CREATE INDEX `req_status_due_idx` ON `requests_app_servicerequest` (`status`, `due_at`);
```

Applied with `python manage.py migrate requests_app`:

```
Applying requests_app.0002_service_level_and_resolution... OK
requests_app
 [X] 0001_initial
 [X] 0002_service_level_and_resolution
```

## 2. MySQL verification

`DESCRIBE requests_app_servicerequest;` (new columns):

| Field | Type | Null |
|---|---|---|
| due_at | datetime(6) | YES |
| resolution_summary | longtext | NO |

`SHOW INDEX FROM requests_app_servicerequest;` (new index):

| Key_name | Seq_in_index | Column_name |
|---|---|---|
| req_status_due_idx | 1 | status |
| req_status_due_idx | 2 | due_at |

Result: the nullable field and the supporting index both exist in MySQL.

Screenshot: `screenshots/mysql-describe-index.png`

## 3. Task 1: Due date

- `due_at` is a nullable `DateTimeField` on `ServiceRequest`.
- Composite index `req_status_due_idx` on `(status, due_at)` supports filtering by status and due date.
- Two synthetic requests were created with different due dates:
  - "Due soon: projector lamp" due in 2 hours
  - "Due later: extension cable" due in 3 days
- Query for requests due before a chosen cutoff (now + 1 day):

```python
cutoff = now + timedelta(days=1)
due_before = ServiceRequest.objects.filter(due_at__lt=cutoff).order_by("due_at")
```

Result:

```
['Broken laboratory socket', 'Due soon: projector lamp']
```

"Due later: extension cable" is correctly excluded because it is due after the cutoff. "Broken laboratory socket" appears because its due date was set earlier during the Admin check.

Generated SQL:

```sql
SELECT `requests_app_servicerequest`.`id`, `requests_app_servicerequest`.`requester_id`, `requests_app_servicerequest`.`category_id`, `requests_app_servicerequest`.`title`, `requests_app_servicerequest`.`description`, `requests_app_servicerequest`.`location`, `requests_app_servicerequest`.`priority`, `requests_app_servicerequest`.`status`, `requests_app_servicerequest`.`resolved_at`, `requests_app_servicerequest`.`due_at`, `requests_app_servicerequest`.`resolution_summary`, `requests_app_servicerequest`.`created_at`, `requests_app_servicerequest`.`updated_at` FROM `requests_app_servicerequest` WHERE `requests_app_servicerequest`.`due_at` < 2026-11-17 20:34:54.019879 ORDER BY `requests_app_servicerequest`.`due_at` ASC
```

### Admin (Task 1)

- `Due at` and `Resolved at` are shown as columns in the Service requests list.
- A custom `OverdueFilter` ("By due date status") offers: Overdue, Due within 24 hours, No due date.
- Overdue strategy: the request is still active (open, assigned or in progress) and `due_at` is before the current time. Filtering on `status` and `due_at` together matches `req_status_due_idx`.

Screenshot:`screenshots/admin-overdue-filter.png`

## 4. Task 2: Resolution summary

- `resolution_summary` is a `TextField(blank=True)`.
- The rule lives in `ServiceRequest.clean()` in `models.py`, which is the domain model, so it applies to `full_clean()`, the Admin form and the tests. It is not placed only in Django Admin.
- Rule: if status is `resolved` or `closed`, then `resolved_at` must be set and `resolution_summary` must not be empty or whitespace only.

Invalid record (resolved, no `resolved_at`, no summary):

```
>>> bad.full_clean()
django.core.exceptions.ValidationError: {'resolved_at': ['Resolved or closed requests require a resolved date and time.'], 'resolution_summary': ['Resolved or closed requests require a resolution summary.']}
```

Valid record (resolved, with `resolved_at` and summary):

```
>>> good.full_clean()
>>> print("valid")
valid
```

Admin: `resolution_summary` is searchable and `resolved_at` is visible in the list. Saving a Resolved request without those fields shows the same errors on the form.

Screenshot:  `screenshots/admin-resolution-error.png`

## 5. Task 3: Query analysis

Synthetic data: 12 requests ("Synthetic request 1" to "Synthetic request 12") across 2 categories (Electrical, ICT Support) and 3 statuses (open, assigned, resolved). Every record passed `full_clean()` before saving. Total requests in the table: 16, including the earlier demonstration records.

Query: open or assigned requests in the Electrical category, ordered by priority then created date.

```python
queryset = (
    ServiceRequest.objects
    .filter(category=electrical, status__in=["open", "assigned"])
    .order_by("priority", "created_at")
)
```

`print(queryset.query)`:

```sql
SELECT `requests_app_servicerequest`.`id`, `requests_app_servicerequest`.`requester_id`, `requests_app_servicerequest`.`category_id`, `requests_app_servicerequest`.`title`, `requests_app_servicerequest`.`description`, `requests_app_servicerequest`.`location`, `requests_app_servicerequest`.`priority`, `requests_app_servicerequest`.`status`, `requests_app_servicerequest`.`resolved_at`, `requests_app_servicerequest`.`due_at`, `requests_app_servicerequest`.`resolution_summary`, `requests_app_servicerequest`.`created_at`, `requests_app_servicerequest`.`updated_at` FROM `requests_app_servicerequest` WHERE (`requests_app_servicerequest`.`category_id` = 1 AND `requests_app_servicerequest`.`status` IN (open, assigned)) ORDER BY `requests_app_servicerequest`.`priority` ASC, `requests_app_servicerequest`.`created_at` ASC
```

`print(queryset.explain())`:

```
-> Sort row IDs: requests_app_servicerequest.priority, requests_app_servicerequest.created_at  (cost=4.11 rows=8)
    -> Index range scan on requests_app_servicerequest using req_cat_status_idx over (category_id = 1 AND status = 'assigned') OR (category_id = 1 AND status = 'open'), with index condition: ((requests_app_servicerequest.category_id = 1) and (requests_app_servicerequest.`status` in ('open','assigned')))  (cost=4.11 rows=8)
```

**Which index is used:** `req_cat_status_idx` on `(category_id, status)`. MySQL ran an index range scan with two ranges, one for `category_id = 1 AND status = 'assigned'` and one for `category_id = 1 AND status = 'open'`. It estimated 8 rows.

**Interpretation:**
- The `WHERE` clause matches the index columns. The equality on `category` and the `IN` on `status` become two narrow ranges, so MySQL did not need a full table scan.
- The `ORDER BY priority, created_at` is not covered by `req_cat_status_idx`, so MySQL adds a separate sort step (`Sort row IDs`, a filesort) after the index lookup.
- The `req_priority_date_idx` index matches the sort order, but it does not help with the filter. MySQL chose the filtering index and sorted the small result afterwards.
- `req_status_due_idx` is not used because this query does not filter on `due_at`.
- Even though the table is small (16 rows), the optimizer still chose an index here, so the "dataset too small" explanation is not needed for this query.

## 6. Tests

Command: `python manage.py test requests_app -v 2`

```
Found 14 test(s).
Ran 14 tests in 2.445s

OK
```

| Test class | Tests | Result |
|---|---|---|
| ServiceRequestModelTests (original) | 5 | ok |
| ServiceLevelAndResolutionTests (new) | 8 | ok |
| OverdueAdminFilterTests (new) | 1 | ok |

Original and new tests all pass. The test run applied migrations `0001` and `0002` to a fresh test database.

## 7. Acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| Migration discipline | Reviewed `0002` applied successfully; `0001` unchanged | Pass |
| Due date | `due_at` column and `req_status_due_idx` shown in MySQL | Pass |
| Resolution rule | Invalid resolved record fails `full_clean()` | Pass |
| Admin | Due date and resolved date in list, overdue filter, summary searchable | Pass |
| Query evidence | `queryset.query` and `explain()` recorded above | Pass |
| Tests | 14 tests pass | Pass |
| Data safety | Only synthetic data used | Pass |