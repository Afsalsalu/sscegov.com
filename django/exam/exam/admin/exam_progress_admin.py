# exam/admin/exam_progress_admin.py

from django.contrib import admin
from django.utils.html import format_html

from exam.models import MainExamProgress


class ExamCategoryFilter(admin.SimpleListFilter):
    title = "Exam Category"
    parameter_name = "exam_category"

    def lookups(self, request, model_admin):
        # Get unique exam categories to display as filter options
        categories = set([p.exam_category for p in model_admin.model.objects.all()])
        return [(c.id, c.name) for c in categories]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(exam_category_id=self.value())
        return queryset


@admin.register(MainExamProgress)
class MainExamProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "total_questions",
        "correct_answers",
        "started_at",
        "completed_at",
        "pass_fail_status",
    )
    list_filter = ("status", "user")  # Filter by status and user
    search_fields = ("user__username",)  # Search by username
    readonly_fields = ("started_at", "completed_at")
    list_per_page = 20
    ordering = ("-started_at",)

    def pass_fail_status(self, obj):
        status_colors = {
            "Passed": "green",
            "Failed Attempt 1": "red",
            "Failed Attempt 2": "red",
            "Not Attempted": "gray",
        }
        color = status_colors.get(obj.status, "gray")
        return format_html('<span style="color: {};">{}</span>', color, obj.status)

    pass_fail_status.short_description = "Exam Status"
