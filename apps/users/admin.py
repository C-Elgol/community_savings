from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Profile, Partners


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_admin')
    list_filter = ('is_staff', 'is_active', 'is_admin', 'is_superuser', 'has_accepted_terms')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'fullname', 'phone_number', 'profile_picture')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_admin', 'has_accepted_terms', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Metadata'), {'fields': ('metadata', 'ip_address', 'is_deleted', 'is_manually_deleted')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password', 'is_staff', 'is_active'),
        }),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'country', 'city', 'region')
    list_filter = ('country', 'region')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'city', 'address')
    raw_id_fields = ('user',)


@admin.register(Partners)
class PartnersAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'is_deleted')
    list_filter = ('is_active', 'is_deleted')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
