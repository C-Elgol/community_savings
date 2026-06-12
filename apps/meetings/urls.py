from django.urls import path

from apps.meetings.views.members_metting_view import MembersMeetingView
from apps.meetings.views.admin_meeting_minute_view import (
    AdminMeetingMinuteView,
    MeetingMinuteAIView,
    MeetingMinuteSaveView,
    MeetingMinuteDetailView,
    MeetingAttendanceAPIView,
    AllMeetingMinutesAPIView,
    MeetingMinutePDFView,
)

app_name = "meetings"
    
urlpatterns = [
    path('meeting/', MembersMeetingView.as_view(), name='members_meeting'),
    path('meeting-minutes/<uuid:community_id>/', AdminMeetingMinuteView.as_view(), name='admin_meeting_minutes'),
    path('meeting-minutes/ai/', MeetingMinuteAIView.as_view(), name='meeting_minutes_ai'),
    path('meeting-minutes/save/', MeetingMinuteSaveView.as_view(), name='meeting_minutes_save'),
    path('meeting-minutes/attendance/save/', MeetingAttendanceAPIView.as_view(), name='meeting_attendance_save'),
    path('meeting-minutes/detail/<uuid:pk>/', MeetingMinuteDetailView.as_view(), name='meeting_minute_detail'),
    path('meeting-minutes/all/<uuid:community_id>/', AllMeetingMinutesAPIView.as_view(), name='all_meeting_minutes'),
    path('meeting-minutes/pdf/<uuid:pk>/', MeetingMinutePDFView.as_view(), name='meeting_minute_pdf'),
]