from django.urls import path
from apps.communities.views.community_view import (
    CommunityListView,
    CommunityCreateView,
    CommunityDetailView,
    CommunityUpdateView,
    CommunityDeleteView,
)
from apps.communities.views.policy_view import (
    CommunityPolicyDetailView,
    CommunityPolicyUpdateView,
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
]