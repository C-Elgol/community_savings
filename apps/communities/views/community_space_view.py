import json
import logging
from django.views.generic import View, TemplateView
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.core.files.storage import default_storage
from django.db.models import Q
from apps.communities.models import CommunitySpace
from apps.global_data.enum import CommunitySpaceStatus
from django.utils.decorators import method_decorator
from apps.log.decorators import log_activity_and_errors

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_LOGO_SIZE_MB = 5


def _validate_logo(file):
    """Validate logo file type and size. Returns error string or None."""
    if file is None:
        return None
    ext = file.name.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return _("Invalid file type. Only JPG, JPEG, PNG, WEBP are allowed.")
    if file.size > MAX_LOGO_SIZE_MB * 1024 * 1024:
        return _("File too large. Maximum size is 5 MB.")
    return None


def _community_space_data(space):
    """Serialize a CommunitySpace instance to a dict for JSON responses."""
    return {
        "id": str(space.id),
        "name": space.name,
        "slug": space.slug,
        "description": space.description or "",
        "status": space.status,
        "status_display": space.get_status_display(),
        "logo_url": space.logo.url if space.logo else "",
        "owner_id": str(space.owner.id) if space.owner else "",
        "owner_name": space.owner.get_full_name if space.owner else "N/A",
        "created": space.created.strftime("%Y-%m-%d") if hasattr(space, "created") else "",
    }


class CommunitySpaceListView(LoginRequiredMixin, TemplateView):
    """Renders the community spaces page with filtering support."""
    template_name = 'publics/superadmin/community_space/community_space.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = CommunitySpace.objects.all().order_by("-created")

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))

        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        ctx.update({
            "spaces": qs,
            "space_statuses": CommunitySpaceStatus.choices,
            "users": User.objects.filter(is_active=True).order_by("email"),
            "search_query": q,
        })
        return ctx


class CommunitySpaceCreateView(LoginRequiredMixin, View):
    """AJAX: Create a new community space."""
    http_method_names = ["post"]

    @method_decorator(log_activity_and_errors())
    def post(self, request, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Bad request."}, status=400)

        data = request.POST
        errors = {}

        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        status = data.get("status", CommunitySpaceStatus.ACTIVE).strip()
        owner_id = data.get("owner", "").strip()
        logo = request.FILES.get("logo")

        if not name:
            errors["name"] = [str(_("Space name is required."))]
        
        if logo:
            logo_error = _validate_logo(logo)
            if logo_error:
                errors["logo"] = [str(logo_error)]

        if errors:
            return JsonResponse({"success": False, "message": str(_("Please fix the errors below.")), "errors": errors}, status=422)

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            owner = User.objects.get(id=owner_id) if owner_id else None

            space = CommunitySpace.objects.create(
                name=name,
                description=description,
                status=status,
                owner=owner,
                created_by=request.user,
            )
            if logo:
                space.logo = logo
                space.save(update_fields=["logo"])

            logger.info("Community Space created: %s by user %s", space.id, request.user.id)
            return JsonResponse({
                "success": True,
                "message": str(_("Community space '%(name)s' created successfully.") % {"name": space.name}),
                "space": _community_space_data(space),
            }, status=201)

        except IntegrityError:
            errors["name"] = [str(_("A community space with this name already exists."))]
            return JsonResponse({"success": False, "message": str(_("Duplicate entry.")), "errors": errors}, status=422)
        except Exception as e:
            logger.exception("Error creating community space")
            return JsonResponse({"success": False, "message": str(_("An unexpected error occurred."))}, status=500)


class CommunitySpaceDetailView(LoginRequiredMixin, View):
    """AJAX: GET a single community space data."""
    http_method_names = ["get"]

    def get(self, request, pk, *args, **kwargs):
        try:
            space = CommunitySpace.objects.get(pk=pk)
            return JsonResponse({"success": True, "space": _community_space_data(space)})
        except CommunitySpace.DoesNotExist:
            return JsonResponse({"success": False, "message": str(_("Space not found."))}, status=404)


class CommunitySpaceUpdateView(LoginRequiredMixin, View):
    """AJAX: Update an existing community space."""
    http_method_names = ["post"]

    @method_decorator(log_activity_and_errors())
    def post(self, request, pk, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Bad request."}, status=400)

        try:
            space = CommunitySpace.objects.get(pk=pk)
        except CommunitySpace.DoesNotExist:
            return JsonResponse({"success": False, "message": str(_("Space not found."))}, status=404)

        data = request.POST
        errors = {}

        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        status = data.get("status", space.status).strip()
        owner_id = data.get("owner", "").strip()
        logo = request.FILES.get("logo")

        if not name:
            errors["name"] = [str(_("Space name is required."))]

        if logo:
            logo_error = _validate_logo(logo)
            if logo_error:
                errors["logo"] = [str(logo_error)]

        if errors:
            return JsonResponse({"success": False, "message": str(_("Please fix the errors below.")), "errors": errors}, status=422)

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            space.name = name
            space.description = description
            space.status = status
            if owner_id:
                space.owner = User.objects.get(id=owner_id)
            else:
                space.owner = None
            
            update_fields = ["name", "description", "status", "owner",]

            if logo:
                if space.logo:
                    try:
                        default_storage.delete(space.logo.name)
                    except: pass
                space.logo = logo
                update_fields.append("logo")

            space.save(update_fields=update_fields)
            return JsonResponse({
                "success": True,
                "message": str(_("Community space updated successfully.")),
                "space": _community_space_data(space),
            })
        except IntegrityError:
            errors["name"] = [str(_("A community space with this name already exists."))]
            return JsonResponse({"success": False, "message": str(_("Duplicate entry.")), "errors": errors}, status=422)
        except Exception:
            logger.exception("Error updating community space")
            return JsonResponse({"success": False, "message": str(_("An unexpected error occurred."))}, status=500)


class CommunitySpaceDeleteView(LoginRequiredMixin, View):
    """AJAX: Delete a community space."""
    http_method_names = ["post"]

    @method_decorator(log_activity_and_errors())
    def post(self, request, pk, *args, **kwargs):
        try:
            space = CommunitySpace.objects.get(pk=pk)
            name = space.name
            space.delete()
            return JsonResponse({"success": True, "message": str(_("Space '%(name)s' deleted.") % {"name": name})})
        except CommunitySpace.DoesNotExist:
            return JsonResponse({"success": False, "message": str(_("Space not found."))}, status=404)
