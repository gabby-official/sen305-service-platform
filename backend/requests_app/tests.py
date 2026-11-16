from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, ServiceRequest, WorkOrder


class ServiceRequestModelTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.requester = user_model.objects.create_user(username="requester")
        self.technician = user_model.objects.create_user(username="technician")
        self.category = Category.objects.create(name="Electrical")

    def make_request(self, **overrides):
        values = {
            "requester": self.requester,
            "category": self.category,
            "title": "Faulty socket",
            "description": "Socket does not supply power.",
            "location": "Software Engineering Lab",
            "priority": 2,
        }
        values.update(overrides)
        return ServiceRequest.objects.create(**values)

    def test_default_status_is_open(self):
        item = self.make_request()
        self.assertEqual(item.status, ServiceRequest.Status.OPEN)

    def test_priority_validator_rejects_zero(self):
        item = ServiceRequest(
            requester=self.requester,
            category=self.category,
            title="Invalid",
            description="Invalid priority.",
            location="Lab",
            priority=0,
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_database_constraint_rejects_priority_six(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_request(priority=6)

    def test_category_in_use_is_protected(self):
        self.make_request()
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_request_accepts_only_one_work_order(self):
        item = self.make_request()
        WorkOrder.objects.create(
            service_request=item,
            technician=self.technician,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WorkOrder.objects.create(
                    service_request=item,
                    technician=self.technician,
                )


class ServiceLevelAndResolutionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.requester = user_model.objects.create_user(username="requester")
        self.category = Category.objects.create(name="Electrical")
        self.now = timezone.now()

    def values(self, **overrides):
        data = {
            "requester": self.requester,
            "category": self.category,
            "title": "Faulty socket",
            "description": "Synthetic laboratory request.",
            "location": "Practice Lab",
            "priority": 2,
        }
        data.update(overrides)
        return data

    def make(self, **overrides):
        return ServiceRequest.objects.create(**self.values(**overrides))

    def build(self, **overrides):
        return ServiceRequest(**self.values(**overrides))

    def test_due_at_is_optional(self):
        self.assertIsNone(self.make().due_at)

    def test_status_due_index_is_declared(self):
        names = [index.name for index in ServiceRequest._meta.indexes]
        self.assertIn("req_status_due_idx", names)

    def test_query_requests_due_before_cutoff(self):
        soon = self.make(title="Due soon", due_at=self.now + timedelta(hours=2))
        self.make(title="Due later", due_at=self.now + timedelta(days=3))
        self.make(title="No due date")
        cutoff = self.now + timedelta(days=1)
        result = ServiceRequest.objects.filter(due_at__lt=cutoff)
        self.assertEqual(list(result), [soon])

    def test_resolved_requires_resolved_at(self):
        item = self.build(
            status=ServiceRequest.Status.RESOLVED,
            resolution_summary="Replaced the breaker.",
        )
        with self.assertRaises(ValidationError) as context:
            item.full_clean()
        self.assertIn("resolved_at", context.exception.message_dict)

    def test_resolved_requires_non_empty_summary(self):
        item = self.build(
            status=ServiceRequest.Status.RESOLVED,
            resolved_at=self.now,
            resolution_summary="   ",
        )
        with self.assertRaises(ValidationError) as context:
            item.full_clean()
        self.assertIn("resolution_summary", context.exception.message_dict)

    def test_closed_requires_both_fields(self):
        item = self.build(status=ServiceRequest.Status.CLOSED)
        with self.assertRaises(ValidationError) as context:
            item.full_clean()
        self.assertIn("resolved_at", context.exception.message_dict)
        self.assertIn("resolution_summary", context.exception.message_dict)

    def test_valid_resolved_request_passes(self):
        item = self.build(
            status=ServiceRequest.Status.RESOLVED,
            resolved_at=self.now,
            resolution_summary="Replaced faulty socket.",
        )
        item.full_clean()

    def test_open_request_needs_no_summary(self):
        self.build(status=ServiceRequest.Status.OPEN).full_clean()


class OverdueAdminFilterTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        admin_user = user_model.objects.create_superuser(
            username="labadmin", password="test-only-password"
        )
        self.client.force_login(admin_user)
        requester = user_model.objects.create_user(username="requester")
        category = Category.objects.create(name="Electrical")
        now = timezone.now()
        base = {
            "requester": requester,
            "category": category,
            "description": "Synthetic laboratory request.",
            "location": "Practice Lab",
        }
        ServiceRequest.objects.create(
            title="Overdue lamp", due_at=now - timedelta(days=1), **base
        )
        ServiceRequest.objects.create(
            title="Future projector", due_at=now + timedelta(days=2), **base
        )
        ServiceRequest.objects.create(
            title="Closed old job",
            due_at=now - timedelta(days=5),
            status=ServiceRequest.Status.CLOSED,
            resolved_at=now - timedelta(days=4),
            resolution_summary="Done.",
            **base,
        )

    def test_overdue_filter_lists_only_active_past_due_requests(self):
        url = reverse("admin:requests_app_servicerequest_changelist")
        response = self.client.get(url, {"due": "overdue"})
        self.assertContains(response, "Overdue lamp")
        self.assertNotContains(response, "Future projector")
        self.assertNotContains(response, "Closed old job")