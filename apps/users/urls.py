from django.urls import path

from apps.users.views.home_view import HomeView
from apps.users.views.member_profile_view import MemberProfileView

app_name = "users"
    
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('profile/', MemberProfileView.as_view(), name='member_profile'),
]