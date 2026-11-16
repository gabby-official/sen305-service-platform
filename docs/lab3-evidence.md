# Lab 3 Evidence

## Database connection
Django reports: `mysql sen305_servicedesk`

## ORM worksheet

| Operation | Observed result |
|---|---|
| Count of all service requests | 2 |
| Count of open requests | 1 |
| Count of assigned requests | 1 |
| Electrical category request count | 2 |
| Technician work-order count | 2 |
| Index or access method shown by explain | Index lookup on `requests_app_servicerequest_status_01cb29e5` (status = 'assigned') |

## Generated SQL and EXPLAIN (K5)

Query:
```python
queryset = ServiceRequest.objects.select_related("requester", "category").filter(status="assigned")
```

SQL from `print(queryset.query)`:
```sql
SELECT `requests_app_servicerequest`.`id`, `requests_app_servicerequest`.`requester_id`, `requests_app_servicerequest`.`category_id`, `requests_app_servicerequest`.`title`, `requests_app_servicerequest`.`description`, `requests_app_servicerequest`.`location`, `requests_app_servicerequest`.`priority`, `requests_app_servicerequest`.`status`, `requests_app_servicerequest`.`resolved_at`, `requests_app_servicerequest`.`created_at`, `requests_app_servicerequest`.`updated_at`, `auth_user`.`id`, `auth_user`.`password`, `auth_user`.`last_login`, `auth_user`.`is_superuser`, `auth_user`.`username`, `auth_user`.`first_name`, `auth_user`.`last_name`, `auth_user`.`email`, `auth_user`.`is_staff`, `auth_user`.`is_active`, `auth_user`.`date_joined`, `requests_app_category`.`id`, `requests_app_category`.`name`, `requests_app_category`.`description`, `requests_app_category`.`is_active`, `requests_app_category`.`created_at` FROM `requests_app_servicerequest` INNER JOIN `auth_user` ON (`requests_app_servicerequest`.`requester_id` = `auth_user`.`id`) INNER JOIN `requests_app_category` ON (`requests_app_servicerequest`.`category_id` = `requests_app_category`.`id`) WHERE `requests_app_servicerequest`.`status` = assigned ORDER BY `requests_app_servicerequest`.`created_at` DESC
```

Note: `print(queryset.query)` shows the parameter as `assigned` without quotes. Django does not quote parameters in this display, and the real query sends it as a quoted string.

Output of `print(queryset.explain())`:
```
-> Nested loop inner join  (cost=1.05 rows=1)
    -> Nested loop inner join  (cost=0.7 rows=1)
        -> Sort row IDs: requests_app_servicerequest.created_at DESC  (cost=0.35 rows=1)
            -> Index lookup on requests_app_servicerequest using requests_app_servicerequest_status_01cb29e5 (status='assigned')  (cost=0.35 rows=1)
        -> Single-row index lookup on requests_app_category using PRIMARY (id=requests_app_servicerequest.category_id)  (cost=0.35 rows=1)
    -> Single-row index lookup on auth_user using PRIMARY (id=requests_app_servicerequest.requester_id)  (cost=0.35 rows=1)
```

### Interpretation
- MySQL used the single-column index on `status` (`requests_app_servicerequest_status_01cb29e5`), created by `db_index=True`, to find the assigned requests.
- It then sorted the matching row IDs by `created_at DESC`, which matches the model's default ordering of `-created_at`.
- The related `Category` and `auth_user` rows were each found with a single-row lookup on their PRIMARY key. These are the joins from `select_related("requester", "category")`.
- Every step estimates `rows=1`, which fits the tiny synthetic dataset.

## Integrity tests

| Test | Expected | Observed |
|---|---|---|
| Duplicate category name | IntegrityError (duplicate entry) | `IntegrityError (1062, "Duplicate entry 'Electrical' for key 'requests_app_category.name'")` |
| Priority 9 via ORM (DB check constraint) | IntegrityError mentioning `request_priority_between_1_and_5` | `IntegrityError (3819, "Check constraint 'request_priority_between_1_and_5' is violated.")` |
| "Invalid priority test" row exists afterwards | False | `False` |
| Priority 0 via `full_clean()` | ValidationError on priority | `ValidationError: {'priority': ['Ensure this value is greater than or equal to 1.']}` |
| Delete Electrical while in use | ProtectedError | `ProtectedError 2` (2 requests reference Electrical) |
| Second work order for same request | IntegrityError (duplicate entry) | `IntegrityError (1062, "Duplicate entry '1d69edf6ef874839a63aa1d5e428e0f0' for key 'requests_app_workorder.service_request_id'")` |

### Summary
- The database rejects a duplicate category name (unique constraint).
- The database CHECK constraint rejects priority 9, and no row was saved.
- Model validators catch priority 0 in `full_clean()` before anything is written to the database.
- `PROTECT` blocks deleting a category that is still in use.
- The one-to-one relation allows only one work order per service request.

Tests

Found 5 test(s).
Creating test database for alias 'default' ('test_sen305_servicedesk')...
Operations to perform:
  Synchronize unmigrated apps: messages, staticfiles
  Apply all migrations: admin, auth, contenttypes, requests_app, sessions
Synchronizing apps without migrations:
  Creating tables...
    Running deferred SQL...
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying admin.0002_logentry_remove_auto_add... OK
  Applying admin.0003_logentry_add_action_flag_choices... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying auth.0009_alter_user_last_name_max_length... OK
  Applying auth.0010_alter_group_name_max_length... OK
  Applying auth.0011_update_proxy_permissions... OK
  Applying auth.0012_alter_user_first_name_max_length... OK
  Applying requests_app.0001_initial... OK
  Applying sessions.0001_initial... OK
System check identified no issues (0 silenced).
test_category_in_use_is_protected (requests_app.tests.ServiceRequestModelTests.test_category_in_use_is_protected) ... ok
test_database_constraint_rejects_priority_six (requests_app.tests.ServiceRequestModelTests.test_database_constraint_rejects_priority_six) ... ok
test_default_status_is_open (requests_app.tests.ServiceRequestModelTests.test_default_status_is_open) ... ok
test_priority_validator_rejects_zero (requests_app.tests.ServiceRequestModelTests.test_priority_validator_rejects_zero) ... ok
test_request_accepts_only_one_work_order (requests_app.tests.ServiceRequestModelTests.test_request_accepts_only_one_work_order) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.219s

OK