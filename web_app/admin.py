from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'school', 'uploaded_at')
    list_filter = ('school', 'uploaded_at')
    search_fields = ('title', 'school__username')
