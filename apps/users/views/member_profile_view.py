from django.views.generic import TemplateView

from django.utils.translation import gettext_lazy as _


class MemberProfileView(TemplateView):
    template_name = 'publics/home/profile/profile.html'
