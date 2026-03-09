from django.contrib import admin
from .models import ActivityLog, FunctionalErrorLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('created', 'user', 'action', 'module', 'status', 'ip_address')
    list_filter = ('status', 'module', 'created')
    search_fields = ('user__email', 'action', 'details', 'ip_address')
    raw_id_fields = ('user',)
    readonly_fields = ('created', 'modified', 'user', 'action', 'module', 'details', 'status', 'user_agent', 'ip_address', 'metadata')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(FunctionalErrorLog)
class FunctionalErrorLogAdmin(admin.ModelAdmin):
    list_display = ('created', 'error_type', 'function_or_view', 'is_resolved', 'ip_address')
    list_filter = ('is_resolved', 'error_type', 'created')
    search_fields = ('error_message', 'function_or_view', 'traceback', 'ip_address')
    raw_id_fields = ('user',)
    list_editable = ('is_resolved',)
    readonly_fields = ('created', 'modified', 'user', 'error_type', 'error_message', 'function_or_view', 'input_data', 'context', 'traceback', 'ip_address', 'metadata')

    def has_add_permission(self, request):
        return False
