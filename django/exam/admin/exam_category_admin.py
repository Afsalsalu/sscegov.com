# exam/admin/exam_category_admin.py
from django.contrib import admin

from exam.admin.option_admin import QuestionInline
from exam.models.exam_category import ExamCategory


@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [QuestionInline]
