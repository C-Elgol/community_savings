import json
import logging
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from openai import OpenAI

from apps.meetings.models import Meeting, MeetingMinute
from apps.communities.models import Community
from apps.global_data.enum import MinuteStatus
from apps.finance.utils.admin_mixins import AdminSeasonMixin

logger = logging.getLogger(__name__)

class AdminMeetingMinuteView(AdminSeasonMixin, LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/meetings_minutes/meetings_minutes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community_id = self.kwargs.get('community_id')
        community = Community.objects.get(id=community_id)
        context['community'] = community
        
        # Fetch last 3 minutes for initial display
        recent_minutes = MeetingMinute.objects.filter(
            meeting__community=community
        ).select_related('meeting', 'prepared_by').order_by('-created')[:3]
        
        context['recent_minutes'] = recent_minutes
        
        # Total count for pagination display (e.g., "3 rows", or for "Load More" logic)
        context['total_minutes_count'] = MeetingMinute.objects.filter(
            meeting__community=community
        ).count()
        
        return context

class MeetingMinuteAIView(LoginRequiredMixin, TemplateView):
    """Handles AI logic: Transcription and Generation"""
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        if action == 'transcribe':
            audio_file = request.FILES.get('audio')
            if not audio_file:
                return JsonResponse({'status': 'error', 'message': 'No file provided'})
            
            ext = audio_file.name.split('.')[-1].lower()
            audio_exts = ['flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']
            
            try:
                if ext in audio_exts:
                    # Use OpenAI Whisper for audio
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=(audio_file.name, audio_file.read())
                    )
                    return JsonResponse({'status': 'success', 'transcript': transcription.text})
                
                elif ext == 'pdf':
                    import pypdf
                    reader = pypdf.PdfReader(audio_file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return JsonResponse({'status': 'success', 'transcript': text.strip()})
                
                elif ext == 'docx':
                    import docx
                    doc = docx.Document(audio_file)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    return JsonResponse({'status': 'success', 'transcript': text.strip()})
                
                elif ext == 'txt':
                    text = audio_file.read().decode('utf-8')
                    return JsonResponse({'status': 'success', 'transcript': text.strip()})
                
                else:
                    return JsonResponse({'status': 'error', 'message': f'Unsupported file format: {ext}'})
                    
            except Exception as e:
                logger.error(f"Transcription/Extraction error: {e}")
                return JsonResponse({'status': 'error', 'message': f"Failed to process {ext} file: {str(e)}"})

        elif action == 'generate':
            transcript = request.POST.get('transcript')
            language = request.POST.get('language', 'English')
            
            if not transcript:
                return JsonResponse({'status': 'error', 'message': 'No transcript provided'})

            try:
                # Use GPT-4 to generate summary and professional minutes
                prompt = f"""
                You are a professional secretary. Based on the following meeting transcript in {language}, 
                please generate exactly two things:
                1. A concise meeting summary.
                2. Professional meeting minutes with sections for attendees (if mentioned), agenda, discussions, and decisions.

                Format your response as a JSON object with keys 'summary' and 'minutes'. 
                IMPORTANT: Both values must be strings. The 'minutes' should be well-formatted with newlines and bullet points.
                
                Transcript:
                {transcript}
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                ai_content = json.loads(response.choices[0].message.content)
                return JsonResponse({
                    'status': 'success', 
                    'summary': ai_content.get('summary'), 
                    'minutes': ai_content.get('minutes')
                })
            except Exception as e:
                logger.error(f"AI Generation error: {e}")
                return JsonResponse({'status': 'error', 'message': str(e)})

        return JsonResponse({'status': 'error', 'message': 'Invalid action'})

class MeetingAttendanceAPIView(LoginRequiredMixin, View):
    """Handles saving/updating attendance for a meeting"""
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            community_id = data.get('community_id')
            date = data.get('date')
            title = data.get('title')
            attendance_list = data.get('attendance', [])

            if not all([community_id, date, title]):
                return JsonResponse({'status': 'error', 'message': 'Missing required fields (Community, Date, Title)'}, status=400)

            community = get_object_or_404(Community, id=community_id)

            from apps.meetings.models import MeetingAttendance
            from apps.communities.models import Membership

            with transaction.atomic():
                # 1. Find or create meeting
                meeting, created = Meeting.objects.get_or_create(
                    community=community,
                    scheduled_date=date,
                    title=title,
                    defaults={
                        'start_time': timezone.now().time(),
                        'end_time': timezone.now().time(),
                        'chaired_by': request.user
                    }
                )

                # 2. Save attendance records
                for record in attendance_list:
                    membership_id = record.get('membership_id')
                    was_present = record.get('was_present', True)
                    
                    membership = get_object_or_404(Membership, id=membership_id)
                    MeetingAttendance.objects.update_or_create(
                        meeting=meeting,
                        membership=membership,
                        defaults={'was_present': was_present}
                    )

            return JsonResponse({
                'status': 'success', 
                'message': 'Attendance saved successfully!', 
                'meeting_id': str(meeting.id)
            })
        except Exception as e:
            logger.error(f"Attendance save error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

class MeetingMinuteSaveView(LoginRequiredMixin, TemplateView):
    """Handles saving meeting and minutes to database"""

    def post(self, request, *args, **kwargs):
        try:
            data = request.POST
            title = data.get('title')
            date = data.get('date')
            language = data.get('language')
            transcript = data.get('transcript')
            summary = data.get('summary')
            minutes_content = data.get('minutes')
            community_id = data.get('community_id')
            meeting_id = data.get('meeting_id')

            if not all([title, date, community_id]):
                return JsonResponse({'status': 'error', 'message': 'Missing required fields (Title, Date, Community)'})

            community = Community.objects.get(id=community_id)

            with transaction.atomic():
                # 1. Create/Update Meeting
                if meeting_id:
                    meeting = get_object_or_404(Meeting, id=meeting_id)
                else:
                    meeting = Meeting.objects.create(
                        community=community,
                        title=title,
                        scheduled_date=date,
                        start_time=timezone.now().time(),
                        end_time=timezone.now().time(), # Placeholder
                        chaired_by=request.user
                    )

                # 2. Create/Update MeetingMinute
                MeetingMinute.objects.update_or_create(
                    meeting=meeting,
                    defaults={
                        'title': title,
                        'minute_date': date,
                        'start_time': meeting.start_time,
                        'end_time': meeting.end_time,
                        'prepared_by': request.user,
                        'transcript': transcript,
                        'summary': summary,
                        'discussions': minutes_content,
                        'language': language,
                        'status': MinuteStatus.DRAFT
                    }
                )

            return JsonResponse({'status': 'success', 'message': 'Meeting minutes saved successfully!'})
        except Exception as e:
            logger.error(f"Save error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})

class MeetingMinuteDetailView(LoginRequiredMixin, TemplateView):
    """Fetches details of a specific meeting minute"""
    def get(self, request, pk, *args, **kwargs):
        try:
            minute = MeetingMinute.objects.get(pk=pk)
            return JsonResponse({
                'status': 'success',
                'title': minute.title,
                'date': minute.minute_date.isoformat() if minute.minute_date else '',
                'language': minute.language,
                'transcript': minute.transcript,
                'summary': minute.summary,
                'minutes': minute.discussions
            })
        except MeetingMinute.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Minute not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
