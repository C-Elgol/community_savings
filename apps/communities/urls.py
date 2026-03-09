from django.urls import path

from apps.communities.views.community_view import CommunityView

app_name = "communities"
    
urlpatterns = [
    path('communities/', CommunityView.as_view(), name='communities'),
]