from django.urls import path

from apps.meetings.views.members_metting_view import MembersMeetingView

app_name = "meetings"
    
urlpatterns = [
    path('meeting/', MembersMeetingView.as_view(), name='members_meeting'),
]