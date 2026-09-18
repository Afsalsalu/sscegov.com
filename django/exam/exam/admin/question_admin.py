# exam/admin/question_admin.py
from django.contrib import admin

from exam.admin.option_admin import (MainExamOptionInline,
                                     OptionInline)
from exam.models.question import MainExamQuestion, Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("question", "exam_category")
    inlines = [OptionInline]


@admin.register(MainExamQuestion)
class MainExamQuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "created_at", "options_count")
    list_filter = ("created_at",)
    search_fields = ("question_text",)
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("question_text",)}),
        ("Dates", {"fields": ("created_at",), "classes": ("collapse",)}),
    )
    inlines = [MainExamOptionInline]

    def options_count(self, obj):
        return obj.options.count()

    options_count.short_description = "Number of Options"
