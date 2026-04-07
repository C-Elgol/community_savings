from django.urls import path

from apps.users.views.home_view import HomeView
from apps.users.views.member_profile_view import MemberProfileView
from apps.users.views.notification_view import NotificationView
from apps.users.views.admin_dashboard_view import AdminDashboardView
from apps.users.views.register_view import RegisterView, Verify2FAView
from apps.users.views.login_view import LoginView, LogoutView
from apps.users.views.password_reset_view import PasswordResetRequestView, PasswordResetVerifyView, PasswordResetView
from apps.users.views.resend_verification_view import ResendVerificationView
from apps.users.views.admin_member_view import AdminMemberView
from apps.users.views.welcome_view import WelcomeView
from apps.users.views.community_space_welcome_view import CommunitySpaceWelcomeView
from apps.users.views.super_admin_user_management_view import (
    SuperAdminUserManagementView,
    AdminUserCreateView,
    AdminUserUpdateView,
    AdminUserToggleStatusView,
    AdminUserDeleteView
)
from apps.users.views.super_admin_dashboard_view import SuperAdminDashboardView
from apps.users.views.membership_application_view import MembershipApplicationView

app_name = "users"
    
urlpatterns = [
    path('', WelcomeView.as_view(), name='welcome'),
    path('home/', WelcomeView.as_view(), name='home'),
    path('space/<uuid:pk>/welcome/', CommunitySpaceWelcomeView.as_view(), name='community_space_welcome'),
    path('dashboard/', HomeView.as_view(), name='dashboard'),
    path('profile/', MemberProfileView.as_view(), name='member_profile'),
    path('notification/', NotificationView.as_view(), name='notification'),
    path('admin-dashboard/<uuid:community_id>/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify-2fa/<str:email>/', Verify2FAView.as_view(), name='verify_2fa'),
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-verify/<str:email>/', PasswordResetVerifyView.as_view(), name='password_reset_verify'),
    path('password-reset/<str:email>/', PasswordResetView.as_view(), name='password_reset'),
    path('resend-verification/<str:email>/', ResendVerificationView.as_view(), name='resend_verification'),
    path('admin-members/<uuid:community_id>/', AdminMemberView.as_view(), name='admin_members'),
    path('superadmin-dashboard/', SuperAdminDashboardView.as_view(), name='superadmin_dashboard'),

    # User Management CRUD
    path('superadmin/user-management/', SuperAdminUserManagementView.as_view(), name='user_management'),
    path('superadmin/user-management/create/', AdminUserCreateView.as_view(), name='user_create'),
    path('superadmin/user-management/<uuid:pk>/update/', AdminUserUpdateView.as_view(), name='user_update'),
    path('superadmin/user-management/<uuid:pk>/toggle-status/', AdminUserToggleStatusView.as_view(), name='user_toggle_status'),
    path('superadmin/user-management/<uuid:pk>/delete/', AdminUserDeleteView.as_view(), name='user_delete'),

    path('membership-application/<uuid:community_id>/', MembershipApplicationView.as_view(), name='membership_application'),
]