from django.conf import settings
from django.db import models

from apps.users.models import SavingsBaseModel
from apps.global_data.enum import MinuteStatus
from apps.communities.models import Community, Membership


class Meeting(SavingsBaseModel):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="meetings")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scheduled_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=255, blank=True)
    chaired_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meetings_chaired"
    )
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-scheduled_date", "-start_time"]

    def __str__(self):
        return f"{self.title} - {self.community.name}"


class MeetingAttendance(SavingsBaseModel):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="attendance_records")
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="attendance_records")
    was_present = models.BooleanField(default=False)
    arrived_late = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = [("meeting", "membership")]


class MeetingMinute(SavingsBaseModel):
    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name="minute")
    title = models.CharField(max_length=255)
    minute_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="minutes_prepared"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="minutes_reviewed"
    )

    opening_remarks = models.TextField(blank=True)
    agenda_summary = models.TextField(blank=True)
    discussions = models.TextField(blank=True)
    decisions = models.TextField(blank=True)
    action_items = models.TextField(blank=True)
    closing_remarks = models.TextField(blank=True)

    # AI & Enhanced Data
    language = models.CharField(max_length=50, default="English", blank=True)
    transcript = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    audio_file = models.FileField(upload_to="meetings/recordings/", null=True, blank=True)

    status = models.CharField(max_length=20, choices=MinuteStatus.choices, default=MinuteStatus.DRAFT)

    def __str__(self):
        return f"Minutes - {self.meeting.title}"


class MinuteResolution(SavingsBaseModel):
    minute = models.ForeignKey(MeetingMinute, on_delete=models.CASCADE, related_name="resolutions")
    title = models.CharField(max_length=255)
    description = models.TextField()
    responsible_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="minute_resolutions"
    )
    due_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title