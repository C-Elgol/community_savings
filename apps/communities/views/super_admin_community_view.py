import logging
import traceback
from typing import Any
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db import transaction, IntegrityError
from django.core.files.storage import default_storage

from apps.communities.models import Community, CommunitySpace
from apps.global_data.enum import CommunityType

logger = logging.getLogger(__name__)

class SuperAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only superadmins can access these views."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('users:dashboard')
        return super().handle_no_permission()

def _validate_logo(file):
    """Validate logo file type and size. Returns error string or None."""
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    MAX_LOGO_SIZE_MB = 5
    if file is None:
        return None
    ext = file.name.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return _("Invalid file type. Only JPG, JPEG, PNG, WEBP are allowed.")
    if file.size > MAX_LOGO_SIZE_MB * 1024 * 1024:
        return _("File too large. Maximum size is 5 MB.")
    return None

class SuperAdminCommunityListView(LoginRequiredMixin, SuperAdminRequiredMixin, TemplateView):
    """
    View to list all communities in the system.
    """
    template_name = 'publics/superadmin/community/community.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch all communities
        communities = Community.objects.all().select_related('community_space').order_by('-created')
        context['communities'] = communities
        context['community_spaces'] = CommunitySpace.objects.filter(status='active')
        context['community_types'] = CommunityType.choices
        return context

class AdminCommunityCreateView(LoginRequiredMixin, SuperAdminRequiredMixin, View):
    """
    View to create a new community manually.
    """
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        community_space_id = request.POST.get('community_space', '').strip()
        community_type = request.POST.get('community_type', '').strip()
        description = request.POST.get('description', '').strip()
        country = request.POST.get('country', '').strip()
        currency = request.POST.get('currency', 'XAF').strip()
        start_date = request.POST.get('start_date', '').strip() or None
        end_date = request.POST.get('end_date', '').strip() or None
        logo = request.FILES.get('logo')

        if not all([name, code, community_space_id, community_type]):
            return JsonResponse({'success': False, 'message': _("Name, code, space, and type are required.")}, status=400)

        space = get_object_or_404(CommunitySpace, id=community_space_id)

        if logo:
            logo_error = _validate_logo(logo)
            if logo_error:
                return JsonResponse({"success": False, "message": logo_error}, status=400)

        try:
            with transaction.atomic():
                community = Community.objects.create(
                    community_space=space,
                    name=name,
                    code=code,
                    community_type=community_type,
                    description=description,
                    country=country,
                    currency=currency,
                    start_date=start_date,
                    end_date=end_date,
                    created_by=request.user
                )
                if logo:
                    community.logo = logo
                    community.save(update_fields=["logo"])
                
            return JsonResponse({'success': True, 'message': _("Community created successfully.")})
        except IntegrityError as e:
            logger.warning(f"IntegrityError creating community: {e}")
            return JsonResponse({'success': False, 'message': _("A community with this name or code already exists in this space.")}, status=400)
        except Exception as e:
            logger.error(f"Error creating community: {e}\n{traceback.format_exc()}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class AdminCommunityUpdateView(LoginRequiredMixin, SuperAdminRequiredMixin, View):
    """
    View to update an existing community.
    """
    def post(self, request: HttpRequest, pk: str, *args: Any, **kwargs: Any) -> HttpResponse:
        community = get_object_or_404(Community, id=pk)
        
        community.name = request.POST.get('name', community.name).strip()
        community.code = request.POST.get('code', community.code).strip().upper()
        community_space_id = request.POST.get('community_space', '').strip()
        if community_space_id:
            community.community_space = get_object_or_404(CommunitySpace, id=community_space_id)
            
        community.community_type = request.POST.get('community_type', community.community_type).strip()
        community.description = request.POST.get('description', community.description).strip()
        community.country = request.POST.get('country', community.country).strip()
        community.currency = request.POST.get('currency', community.currency).strip()
        community.start_date = request.POST.get('start_date', '').strip() or None
        community.end_date = request.POST.get('end_date', '').strip() or None
        logo = request.FILES.get('logo')

        if logo:
            logo_error = _validate_logo(logo)
            if logo_error:
                return JsonResponse({"success": False, "message": logo_error}, status=400)
            
            if community.logo:
                try:
                    default_storage.delete(community.logo.name)
                except Exception:
                    pass
            community.logo = logo

        try:
            community.save()
            return JsonResponse({'success': True, 'message': _("Community updated successfully.")})
        except IntegrityError as e:
            return JsonResponse({'success': False, 'message': _("A community with this name or code already exists in this space.")}, status=400)
        except Exception as e:
            logger.error(f"Error updating community {pk}: {e}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class AdminCommunityDeleteView(LoginRequiredMixin, SuperAdminRequiredMixin, View):
    """
    View to delete a community.
    """
    def post(self, request: HttpRequest, pk: str, *args: Any, **kwargs: Any) -> HttpResponse:
        community = get_object_or_404(Community, id=pk)
        name = community.name
        community.delete()
        return JsonResponse({'success': True, 'message': _("Community '{name}' deleted successfully.").format(name=name)})
