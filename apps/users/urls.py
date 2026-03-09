from django.urls import path

from apps.users.views.home_view import HomeView
from apps.users.views.member_profile_view import MemberProfileView
from apps.users.views.notification_view import NotificationView
from apps.users.views.admin_dashboard_view import AdminDashboardView
from apps.users.views.register_view import RegisterView
from apps.users.views.login_view import LoginView

app_name = "users"
    
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('profile/', MemberProfileView.as_view(), name='member_profile'),
    path('notification/', NotificationView.as_view(), name='notification'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
]