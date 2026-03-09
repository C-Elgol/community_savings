from django.contrib import admin
from .models import Meeting, MeetingAttendance, MeetingMinute, MinuteResolution


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'community', 'scheduled_date', 'start_time', 'venue', 'is_closed')
    list_filter = ('community', 'is_closed', 'scheduled_date')
    search_fields = ('title', 'description', 'venue')
    raw_id_fields = ('community', 'chaired_by')
    date_hierarchy = 'scheduled_date'


@admin.register(MeetingAttendance)
class MeetingAttendanceAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'membership', 'was_present', 'arrived_late')
    list_filter = ('was_present', 'arrived_late', 'meeting__community')
    raw_id_fields = ('meeting', 'membership')


class MinuteResolutionInline(admin.TabularInline):
    model = MinuteResolution
    extra = 1


@admin.register(MeetingMinute)
class MeetingMinuteAdmin(admin.ModelAdmin):
    list_display = ('title', 'meeting', 'minute_date', 'status', 'prepared_by')
    list_filter = ('status', 'minute_date')
    search_fields = ('title', 'agenda_summary', 'discussions', 'decisions')
    raw_id_fields = ('meeting', 'prepared_by', 'reviewed_by')
    inlines = [MinuteResolutionInline]


@admin.register(MinuteResolution)
class MinuteResolutionAdmin(admin.ModelAdmin):
    list_display = ('title', 'minute', 'responsible_person', 'due_date', 'is_completed')
    list_filter = ('is_completed', 'due_date')
    search_fields = ('title', 'description')
    raw_id_fields = ('minute', 'responsible_person')
