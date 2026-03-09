from django.urls import path

from apps.users.views.home_view import HomeView
from apps.users.views.member_profile_view import MemberProfileView
from apps.users.views.notification_view import NotificationView
from apps.users.views.admin_dashboard_view import AdminDashboardView
from apps.users.views.register_view import RegisterView, Verify2FAView
from apps.users.views.login_view import LoginView
from apps.users.views.password_reset_view import PasswordResetRequestView, PasswordResetVerifyView, PasswordResetView
from apps.users.views.resend_verification_view import ResendVerificationView


app_name = "users"
    
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('profile/', MemberProfileView.as_view(), name='member_profile'),
    path('notification/', NotificationView.as_view(), name='notification'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('verify-2fa/<str:email>/', Verify2FAView.as_view(), name='verify_2fa'),
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-verify/<str:email>/', PasswordResetVerifyView.as_view(), name='password_reset_verify'),
    path('password-reset/<str:email>/', PasswordResetView.as_view(), name='password_reset'),
    path('resend-verification/<str:email>/', ResendVerificationView.as_view(), name='resend_verification'),
]