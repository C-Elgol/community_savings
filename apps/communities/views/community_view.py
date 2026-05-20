import json
import logging
from django.views.generic import View, TemplateView
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.core.files.storage import default_storage
from apps.communities.models import Community
from apps.global_data.enum import CommunityType
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


def _community_data(community):
    """Serialize a Community instance to a dict for JSON responses."""
    # Ensure dates are in ISO format regardless of whether they are objects or strings
    def format_date(dt):
        if not dt:
            return ""
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        return str(dt)

    return {
        "id": str(community.id),
        "name": community.name,
        "code": community.code,
        "description": community.description or "",
        "community_type": community.community_type,
        "community_type_display": community.get_community_type_display(),
        "country": community.country or "",
        "currency": community.currency,
        "start_date": format_date(community.start_date),
        "end_date": format_date(community.end_date),
        "logo_url": community.logo.url if community.logo else "",
        "member_count": community.memberships.filter(status="active").count(),
        "created": community.created.strftime("%b %Y") if hasattr(community, "created") else "",
    }


class CommunityListView(LoginRequiredMixin, TemplateView):
    """Renders the communities page with search + type filter support."""
    template_name = "publics/admin/communities/community.html"

    def get_template_names(self):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' or self.request.GET.get('partial'):
            return ["publics/admin/communities/includes/_community_list.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.db.models import Count, Q
        from django.core.paginator import Paginator

        qs = Community.objects.annotate(
            active_member_count=Count('memberships', filter=Q(memberships__status='active'))
        ).order_by("-created")

        q = self.request.GET.get("q", "").strip()
        selected_type = self.request.GET.get("type", "")

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(country__icontains=q))
        if selected_type:
            qs = qs.filter(community_type=selected_type)

        paginator = Paginator(qs, 12)
        page_number = self.request.GET.get("page", 1)
        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            page_number = 1
        communities = paginator.get_page(page_number)

        from apps.global_data.enum import RegistrationFeeMode, ContributionFrequency

        ctx.update({
            "communities": communities,
            "community_types": CommunityType.choices,
            "registration_fee_modes": RegistrationFeeMode.choices,
            "contribution_frequencies": ContributionFrequency.choices,
            "search_query": q,
            "selected_type": selected_type,
            "total_count": paginator.count,
        })
        return ctx


# Alias for the URL that expects CommunityView
CommunityView = CommunityListView


class CommunityCreateView(LoginRequiredMixin, View):
    """AJAX: Create a new community. POST multipart/form-data."""
    http_method_names = ["post"]

    @method_decorator(log_activity_and_errors())
    def post(self, request, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Bad request."}, status=400)

        data = request.POST
        errors = {}

        name = data.get("name", "").strip()
        code = data.get("code", "").strip().upper()
        community_type = data.get("community_type", "").strip()
        description = data.get("description", "").strip()
        country = data.get("country", "").strip()
        currency = data.get("currency", "XAF").strip()
        start_date = data.get("start_date", "").strip() or None
        end_date = data.get("end_date", "").strip() or None
        logo = request.FILES.get("logo")

        # --- Validation ---
        if not name:
            errors["name"] = [str(_("Community name is required."))]
        if not code:
            errors["code"] = [str(_("Community code is required."))]
        if not community_type or community_type not in dict(CommunityType.choices):
            errors["community_type"] = [str(_("A valid community type is required."))]

        # Space association
        space_id = data.get("community_space_pk") or data.get("community_space")
        if not space_id:
            errors["community_space"] = [str(_("Community space is required."))]
        else:
            try:
                from apps.communities.models import CommunitySpace
                space = CommunitySpace.objects.get(pk=space_id)
            except (CommunitySpace.DoesNotExist, ValueError):
                errors["community_space"] = [str(_("Invalid community space."))]

        if logo:
            logo_error = _validate_logo(logo)
            if logo_error:
                errors["logo"] = [str(logo_error)]

        if errors:
            return JsonResponse({"success": False, "message": str(_("Please fix the errors below.")), "errors": errors}, status=422)

        try:
            community = Community.objects.create(
                community_space=space,
                name=name,
                code=code,
                community_type=community_type,
                description=description,
                country=country,
                currency=currency,
                start_date=start_date or None,
                end_date=end_date or None,
                created_by=request.user,
            )
            if logo:
                community.logo = logo
                community.save(update_fields=["logo"])

            logger.info("Community created: %s by user %s", community.id, request.user.id)
            return JsonResponse({
                "success": True,
                "message": str(_("Community '%(name)s' created successfully.") % {"name": community.name}),
                "community": _community_data(community),
            }, status=201)

        except IntegrityError as e:
            logger.warning("IntegrityError creating community: %s", e)
            err_str = str(e).lower()
            if "name" in err_str:
                errors["name"] = [str(_("A community with this name already exists."))]
            elif "code" in err_str:
                errors["code"] = [str(_("A community with this code already exists."))]
            else:
                errors["__all__"] = [str(_("A community with this name or code already exists."))]
            return JsonResponse({"success": False, "message": str(_("Duplicate entry.")), "errors": errors}, status=422)
        except Exception as e:
            logger.exception("Unexpected error creating community")
            return JsonResponse({"success": False, "message": str(_("An unexpected error occurred. Please try again."))}, status=500)


class CommunityDetailView(LoginRequiredMixin, View):
    """AJAX: GET a single community's data for populating the edit drawer."""
    http_method_names = ["get"]

    def get(self, request, pk, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Bad request."}, status=400)
        try:
            community = Community.objects.get(pk=pk)
            return JsonResponse({"success": True, "community": _community_data(community)})
        except Community.DoesNotExist:
            return JsonResponse({"success": False, "message": str(_("Community not found."))}, status=404)


class CommunityUpdateView(LoginRequiredMixin, View):
    """AJAX: Update an existing community (POST multipart/form-data)."""
    http_method_names = ["post"]

    @method_decorator(log_activity_and_errors())
    def post(self, request, pk, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Bad request."}, status=400)

        try:
            community = Community.objects.get(pk=pk)
        except Community.DoesNotExist:
            return JsonResponse({"success": False, "message": str(_("Community not found."))}, status=404)

        data = request.POST
        errors = {}

        name = data.get("name", "").strip()
        code = data.get("code", "").strip().upper()
        community_type = data.get("community_type", "").strip()
        description = data.get("description", "").strip()
        country = data.get("country", "").strip()
        currency = data.get("currency", community.currency).strip()
        start_date = data.get("start_date", "").strip() or None
        end_date = data.get("end_date", "").strip() or None
        logo = request.FILES.get("logo")

        if not name:
            errors["name"] = [str(_("Community name is required."))]
        if not code:
            errors["code"] = [str(_("Community code is required."))]
        if not community_type or community_type not in dict(CommunityType.choices):
            errors["community_type"] = [str(_("A valid community type is required."))]

        if logo:
            logo_error = _validate_logo(logo)
            if logo_error:
                errors["logo"] = [str(logo_error)]

        if errors:
            return JsonResponse({"success": False, "message": str(_("Please fix the errors below.")), "errors": errors}, status=422)

        try:
            # Track if name/code conflict with another community
            community.name = name
            community.code = code
            community.community_type = community_type
            community.description = description
            community.country = country
            community.currency = currency
            community.start_date = start_date or None
            community.end_date = end_date or None
            update_fields = ["name", "code", "community_type", "description", "country", "currency", "start_date", "end_date"]

            if logo:
                # Delete old logo if exists
                if community.logo:
                    try:
                        default_storage.delete(community.logo.name)
                    except Exception:
                        pass
                community.logo = logo
                update_fields.append("logo")

            community.save(update_fields=update_fields)
            logger.info("Community updated: %s by user %s", community.id, request.user.id)
            return JsonResponse({
                "success": True,
                "message": str(_("Community '%(name)s' updated successfully.") % {"name": community.name}),
                "community": _community_data(community),
            })

        except IntegrityError as e:
            logger.warning("IntegrityError updating community %s: %s", pk, e)
            err_str = str(e).lower()
            if "name" in err_str:
                errors["name"] = [str(_("A community with this name already exists."))]
            elif "code" in err_str:
                errors["code"] = [str(_("A community with this code already exists."))]
            else:
                errors["__all__"] = [str(_("A community with this name or code already exists."))]
            return JsonResponse({"success": False, "message": str(_("Duplicate entry.")), "errors": errors}, status=422)
        except Exception:
            logger.exception("Unexpected error updating community %s", pk)
            return JsonResponse({"success": False, "message": str(_("An unexpected error occurred. Please try again."))}, status=500)


class CommunityDeleteView(LoginRequiredMixin, View):
    """AJAX: Soft-delete (or hard-delete) a community."""
    http_method_names = ["post"]

    @method_decorator(log_activity_and_errors())
    def post(self, request, pk, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Bad request."}, status=400)
        try:
            community = Community.objects.get(pk=pk)
            name = community.name
            community_id = str(community.id)
            community.delete()
            logger.info("Community deleted: %s (%s) by user %s", community_id, name, request.user.id)
            return JsonResponse({
                "success": True,
                "message": str(_("Community '%(name)s' deleted successfully.") % {"name": name}),
                "deleted_id": community_id,
            })
        except Community.DoesNotExist:
            return JsonResponse({"success": False, "message": str(_("Community not found."))}, status=404)
        except Exception:
            logger.exception("Unexpected error deleting community %s", pk)
            return JsonResponse({"success": False, "message": str(_("An unexpected error occurred. Please try again."))}, status=500)
