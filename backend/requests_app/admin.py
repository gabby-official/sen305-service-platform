from datetime import timedelta

from django.contrib import admin
from django.utils import timezone

from .models import Category, Comment, ServiceRequest, WorkOrder


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("author", "body", "is_internal", "created_at")
    readonly_fields = ("created_at",)


class OverdueFilter(admin.SimpleListFilter):
    """Overdue strategy: still active (not resolved/closed) and past due_at.

    Filtering on status and due_at together matches req_status_due_idx.
    """

    title = "due date status"
    parameter_name = "due"

    ACTIVE = (
        ServiceRequest.Status.OPEN,
        ServiceRequest.Status.ASSIGNED,
        ServiceRequest.Status.IN_PROGRESS,
    )

    def lookups(self, request, model_admin):
        return (
            ("overdue", "Overdue"),
            ("soon", "Due within 24 hours"),
            ("none", "No due date"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "overdue":
            return queryset.filter(status__in=self.ACTIVE, due_at__lt=now)
        if self.value() == "soon":
            return queryset.filter(
                status__in=self.ACTIVE,
                due_at__gte=now,
                due_at__lte=now + timedelta(hours=24),
            )
        if self.value() == "none":
            return queryset.filter(due_at__isnull=True)
        return queryset


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "title", "category", "requester", "priority", "status",
        "due_at", "resolved_at", "created_at",
    )
    list_filter = ("status", "priority", "category", OverdueFilter)
    search_fields = (
        "title", "description", "location", "resolution_summary",
        "requester__username",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("requester", "category")
    date_hierarchy = "created_at"
    inlines = (CommentInline,)


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("service_request", "technician", "started_at", "completed_at")
    search_fields = ("service_request__title", "technician__username")
    autocomplete_fields = ("service_request", "technician")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("service_request", "author", "is_internal", "created_at")
    list_filter = ("is_internal", "created_at")
    search_fields = ("body", "service_request__title", "author__username")