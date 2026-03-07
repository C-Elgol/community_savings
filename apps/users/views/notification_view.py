from django.views.generic import TemplateView

from django.utils.translation import gettext_lazy as _


class NotificationView(TemplateView):
    template_name = 'publics/home/notification/notification.html'
