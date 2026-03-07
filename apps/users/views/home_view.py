from django.views.generic import TemplateView

from django.utils.translation import gettext_lazy as _


class HomeView(TemplateView):
    template_name = 'publics/home/dashboard.html'
