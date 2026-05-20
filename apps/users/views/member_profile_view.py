from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db import transaction
import logging
from django.utils.translation import gettext_lazy as _
from apps.users.models import Profile
from django.utils.decorators import method_decorator
from apps.log.decorators import log_activity_and_errors

logger = logging.getLogger(__name__)


class MemberProfileView(LoginRequiredMixin, TemplateView):
    template_name = "publics/home/profile/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Ensure profile exists
        profile, created = Profile.objects.get_or_create(user=user)
        context["user_profile"] = profile
        return context

    @method_decorator(log_activity_and_errors())
    def post(self, request, *args, **kwargs):
        user = request.user
        profile = getattr(user, "profile", None)
        if not profile:
            profile = Profile.objects.create(user=user)

        # Get data from request.POST
        fullname = request.POST.get("fullname")
        phone_number = request.POST.get("phone_number")
        country = request.POST.get("country")
        region = request.POST.get("region")
        city = request.POST.get("city")
        address = request.POST.get("address")
        zip_code = request.POST.get("zip_code")
        profile_picture = request.FILES.get("profile_picture")

        try:
            with transaction.atomic():
                # Update User fields
                if fullname:
                    user.fullname = fullname
                if phone_number:
                    user.phone_number = phone_number
                if profile_picture:
                    user.profile_picture = profile_picture
                user.save()

                # Update Profile fields
                profile.country = country or profile.country
                profile.region = region or profile.region
                profile.city = city or profile.city
                profile.address = address or profile.address
                profile.zip_code = zip_code or profile.zip_code
                profile.save()

            return JsonResponse(
                {"status": "success", "message": _("Profile updated successfully!")}
            )
        except Exception as e:
            logger.error(f"Error updating profile for user {user.email}: {str(e)}")
            return JsonResponse(
                {
                    "status": "error",
                    "message": _("An error occurred while updating your profile."),
                },
                status=400,
            )
