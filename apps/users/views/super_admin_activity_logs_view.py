from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from apps.log.models import ActivityLog
import logging

logger = logging.getLogger(__name__)

class SuperAdminActivityLogsView(LoginRequiredMixin, ListView):
    template_name = 'publics/superadmin/activity_logs/activity_logs.html'
    model = ActivityLog
    context_object_name = 'logs'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().order_by('-created')
        
        search = self.request.GET.get('search', '').strip()
        module = self.request.GET.get('module', '').strip()
        status = self.request.GET.get('status', '').strip()
        start_date = self.request.GET.get('start_date', '').strip()
        end_date = self.request.GET.get('end_date', '').strip()

        if search:
            qs = qs.filter(
                Q(action__icontains=search) |
                Q(user__email__icontains=search) |
                Q(details__icontains=search)
            )
        if module:
            qs = qs.filter(module__iexact=module)
        if status:
            qs = qs.filter(status__iexact=status)
        if start_date:
            qs = qs.filter(created__date__gte=start_date)
        if end_date:
            qs = qs.filter(created__date__lte=end_date)
            
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filters'] = {
            'search': self.request.GET.get('search', ''),
            'module': self.request.GET.get('module', ''),
            'status': self.request.GET.get('status', ''),
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', '')
        }
        
        # Get distinct modules and statuses for the dropdowns
        ctx['modules'] = ActivityLog.objects.exclude(module__isnull=True).exclude(module='').values_list('module', flat=True).distinct()
        
        return ctx
