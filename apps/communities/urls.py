from django.urls import path
from apps.communities.views.community_view import (
    CommunityListView,
    CommunityCreateView,
    CommunityDetailView,
    CommunityUpdateView,
    CommunityDeleteView,
)
from apps.communities.views.settings_view import (
    AdminSettingsView,
    UpdateFeatureStatusAPI,
    UpdateCommunitySettingsAPI,
)
from apps.communities.views.policy_view import (
    CommunityPolicyDetailView,
    CommunityPolicyUpdateView,
)
from apps.communities.views.community_space_view import (
    CommunitySpaceListView,
    CommunitySpaceCreateView,
    CommunitySpaceDetailView,
    CommunitySpaceUpdateView,
    CommunitySpaceDeleteView,
)
from apps.communities.views.member_api_view import (
    MemberListAPI,
    MemberCreateAPI,
    MemberDetailAPI,
    MemberUpdateAPI,
    MemberDeleteAPI,
    EligibleFeatureMemberAPI,
    AddMemberToFeatureAPI,
    RemoveMemberFromFeatureAPI,
)
from apps.communities.views.super_admin_community_view import (
    SuperAdminCommunityListView,
    AdminCommunityCreateView,
    AdminCommunityUpdateView,
    AdminCommunityDeleteView,
)
from apps.communities.views.application_api_view import (
    ApplicationListAPI,
    ApplicationDetailAPI,
    ApplicationProcessAPI,
    ApplicationCreateAPI,
)

app_name = "communities"

urlpatterns = [
    path("communities/", CommunityListView.as_view(), name="communities"),
    path("communities/create/", CommunityCreateView.as_view(), name="community_create"),
    path("communities/<uuid:pk>/", CommunityDetailView.as_view(), name="community_detail"),
    path("communities/<uuid:pk>/update/", CommunityUpdateView.as_view(), name="community_update"),
    path("communities/<uuid:pk>/delete/", CommunityDeleteView.as_view(), name="community_delete"),

    # Policies
    path("communities/<uuid:community_pk>/policy/", CommunityPolicyDetailView.as_view(), name="policy_detail"),
    path("communities/<uuid:community_pk>/policy/update/", CommunityPolicyUpdateView.as_view(), name="policy_update"),

    # Community Space
    path("communities-space", CommunitySpaceListView.as_view(), name="community_space"),
    path("communities-space/create/", CommunitySpaceCreateView.as_view(), name="community_space_create"),
    path("communities-space/<uuid:pk>/", CommunitySpaceDetailView.as_view(), name="community_space_detail"),
    path("communities-space/<uuid:pk>/update/", CommunitySpaceUpdateView.as_view(), name="community_space_update"),
    path("communities-space/<uuid:pk>/delete/", CommunitySpaceDeleteView.as_view(), name="community_space_delete"),

    # Member API
    path("api/communities/<uuid:community_id>/members/", MemberListAPI.as_view(), name="member_list_api"),
    path("api/communities/<uuid:community_id>/members/create/", MemberCreateAPI.as_view(), name="member_create_api"),
    path("api/members/<uuid:member_id>/", MemberDetailAPI.as_view(), name="member_detail_api"),
    path("api/members/<uuid:member_id>/update/", MemberUpdateAPI.as_view(), name="member_update_api"),
    path("api/members/<uuid:member_id>/delete/", MemberDeleteAPI.as_view(), name="member_delete_api"),
    
    # Feature Membership API
    path("api/communities/<uuid:community_id>/features/<str:feature_type>/eligible-members/", EligibleFeatureMemberAPI.as_view(), name="eligible_feature_members_api"),
    path("api/communities/<uuid:community_id>/features/<str:feature_type>/add-members/", AddMemberToFeatureAPI.as_view(), name="add_members_to_feature_api"),
    path("api/communities/<uuid:community_id>/features/<str:feature_type>/remove-member/", RemoveMemberFromFeatureAPI.as_view(), name="remove_member_from_feature_api"),

    # Application API
    path("api/communities/<uuid:community_id>/applications/", ApplicationListAPI.as_view(), name="application_list_api"),
    path("api/applications/<uuid:application_id>/", ApplicationDetailAPI.as_view(), name="application_detail_api"),
    path("api/applications/<uuid:application_id>/process/", ApplicationProcessAPI.as_view(), name="application_process_api"),
    path("api/communities/<uuid:community_id>/apply/", ApplicationCreateAPI.as_view(), name="application_create_api"),

    # Settings
    path("communities/<uuid:community_id>/settings/", AdminSettingsView.as_view(), name="settings"),
    path("api/communities/<uuid:community_id>/features/toggle/", UpdateFeatureStatusAPI.as_view(), name="toggle_feature_api"),
    path("api/communities/<uuid:community_id>/settings/update/", UpdateCommunitySettingsAPI.as_view(), name="update_settings_api"),

    # SuperAdmin Community Management
    path("superadmin/communities/", SuperAdminCommunityListView.as_view(), name="superadmin_communities"),
    path("superadmin/communities/create/", AdminCommunityCreateView.as_view(), name="superadmin_community_create"),
    path("superadmin/communities/<uuid:pk>/update/", AdminCommunityUpdateView.as_view(), name="superadmin_community_update"),
    path("superadmin/communities/<uuid:pk>/delete/", AdminCommunityDeleteView.as_view(), name="superadmin_community_delete"),
]