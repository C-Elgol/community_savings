from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
import logging
from apps.communities.models import Membership
from apps.meetings.models import Meeting, MeetingAttendance

logger = logging.getLogger(__name__)

class MembersMeetingView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/home/meeting/meeting.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get primary membership
        membership = Membership.objects.filter(user=user, status='active').first()
        if not membership:
            context['no_membership'] = True
            return context
            
        today = timezone.now().date()
        
        # Upcoming Meetings (Scheduled for today or later)
        upcoming_meetings = Meeting.objects.filter(
            community=membership.community,
            scheduled_date__gte=today
        ).order_by('scheduled_date', 'start_time')
        
        # Past Meetings
        past_meetings = Meeting.objects.filter(
            community=membership.community,
            scheduled_date__lt=today
        ).order_by('-scheduled_date', '-start_time')
        
        # Annotate meetings with user attendance status
        # We'll fetch all relevant attendance for this user at once
        attendance_map = {
            a.meeting_id: a 
            for a in MeetingAttendance.objects.filter(membership=membership)
        }
        
        context['upcoming_meetings'] = upcoming_meetings
        
        # For past meetings, combine with attendance info
        history = []
        for m in past_meetings:
            attendance = attendance_map.get(m.id)
            history.append({
                'meeting': m,
                'attendance': attendance,
                'has_minutes': hasattr(m, 'minute') and m.minute.status == 'final'
            })
            
        context['past_meetings_history'] = history
        context['membership'] = membership
        
        return context
