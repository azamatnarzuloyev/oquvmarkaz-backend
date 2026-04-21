from django.contrib import admin
from .models import Lead, LeadActivity


class LeadActivityInline(admin.TabularInline):
    model  = LeadActivity
    extra  = 0
    fields = ('type', 'content', 'created_by', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display   = ('full_name', 'phone', 'source', 'status', 'assigned_to', 'created_at')
    list_filter    = ('status', 'source', 'created_at')
    search_fields  = ('full_name', 'phone')
    ordering       = ('-created_at',)
    inlines        = (LeadActivityInline,)
    readonly_fields = ('converted_at', 'created_at', 'updated_at')
