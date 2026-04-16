import json
import logging
from django.views.generic import TemplateView
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

logger = logging.getLogger(__name__)

class AdminMeetingMinuteView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/meetings_minutes/meetings_minutes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community_id = self.kwargs.get('community_id')
        community = Community.objects.get(id=community_id)
        context['community'] = community
        return context

class MeetingMinuteAIView(LoginRequiredMixin, TemplateView):
    """Handles AI logic: Transcription and Generation"""
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        if action == 'transcribe':
            audio_file = request.FILES.get('audio')
            if not audio_file:
                return JsonResponse({'status': 'error', 'message': 'No audio file provided'})
            
            try:
                # Use OpenAI Whisper
                # We pass a tuple (filename, file_content) to satisfy the library requirements
                transcription = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=(audio_file.name, audio_file.read())
                )
                return JsonResponse({'status': 'success', 'transcript': transcription.text})
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                return JsonResponse({'status': 'error', 'message': str(e)})

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

            if not all([title, date, community_id]):
                return JsonResponse({'status': 'error', 'message': 'Missing required fields (Title, Date, Community)'})

            community = Community.objects.get(id=community_id)

            with transaction.atomic():
                # 1. Create/Update Meeting
                # In this flow, we create a new meeting record
                meeting = Meeting.objects.create(
                    community=community,
                    title=title,
                    scheduled_date=date,
                    start_time=timezone.now().time(),
                    end_time=timezone.now().time(), # Placeholder
                    chaired_by=request.user
                )

                # 2. Create MeetingMinute
                MeetingMinute.objects.create(
                    meeting=meeting,
                    title=title,
                    minute_date=date,
                    start_time=meeting.start_time,
                    end_time=meeting.end_time,
                    prepared_by=request.user,
                    transcript=transcript,
                    summary=summary,
                    discussions=minutes_content,
                    language=language,
                    status=MinuteStatus.DRAFT
                )

            return JsonResponse({'status': 'success', 'message': 'Meeting minutes saved successfully!'})
        except Exception as e:
            logger.error(f"Save error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
