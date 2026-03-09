from django.contrib import admin
from .models import Community, CommunityPolicy, MembershipApplication, Membership


class CommunityPolicyInline(admin.StackedInline):
    model = CommunityPolicy
    can_delete = False
    verbose_name_plural = 'Policy'


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'community_type', 'country', 'start_date', 'status')
    list_filter = ('community_type', 'country', 'status', 'is_deleted')
    search_fields = ('name', 'code', 'description')
    inlines = [CommunityPolicyInline]
    raw_id_fields = ('created_by',)


@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'applied_role', 'status', 'registration_fee_paid', 'approved_at')
    list_filter = ('status', 'applied_role', 'registration_fee_paid')
    search_fields = ('user__email', 'community__name', 'rejection_reason')
    raw_id_fields = ('community', 'user', 'approved_by')
    date_hierarchy = 'created'


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'role', 'status', 'joined_at', 'member_code')
    list_filter = ('status', 'role', 'community')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'member_code', 'member_id_number')
    raw_id_fields = ('community', 'user', 'application')
    date_hierarchy = 'joined_at'
