from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from apps.communities.models import Community, CommunitySpace, CommunitySpaceMembership
from apps.global_data.enum import CommunitySpaceRole, CommunityType
from apps.users.permissions import has_area_permission, rbac_permission_required
from django.http import JsonResponse
import uuid

User = get_user_model()

class RBACPermissionTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='test@example.com', password='password')
        self.space = CommunitySpace.objects.create(name='Test Space', slug='test-space')
        self.community = Community.objects.create(
            community_space=self.space, 
            name='Test Community', 
            code='TC01', 
            community_type=CommunityType.NJANGI
        )

    def test_has_area_permission(self):
        # Owner should have everything
        self.assertTrue(has_area_permission(CommunitySpaceRole.OWNER, 'dashboard'))
        self.assertTrue(has_area_permission(CommunitySpaceRole.OWNER, 'logs'))
        
        # Secretary should have meetings but not loans
        self.assertTrue(has_area_permission(CommunitySpaceRole.SECRETARY, 'meetings'))
        self.assertFalse(has_area_permission(CommunitySpaceRole.SECRETARY, 'loans'))
        
        # Auditor should have read-only permissions
        self.assertTrue(has_area_permission(CommunitySpaceRole.AUDITOR, 'reports'))

    def test_rbac_decorator_authorized(self):
        # Assign Secretary role
        CommunitySpaceMembership.objects.create(
            community_space=self.space,
            user=self.user,
            role=CommunitySpaceRole.SECRETARY
        )
        
        @rbac_permission_required('meetings')
        def test_view(request, community_id):
            return JsonResponse({'success': True})
            
        request = self.factory.get(f'/admin/{self.community.id}/meetings/')
        request.user = self.user
        request.session = {}
        
        response = test_view(request, community_id=self.community.id)
        self.assertEqual(response.status_code, 200)

    def test_rbac_decorator_unauthorized(self):
        # Assign Secretary role
        CommunitySpaceMembership.objects.create(
            community_space=self.space,
            user=self.user,
            role=CommunitySpaceRole.SECRETARY
        )
        
        # Try to access loans
        @rbac_permission_required('loans')
        def test_view(request, community_id):
            return JsonResponse({'success': True})
            
        request = self.factory.get(f'/admin/{self.community.id}/loans/')
        request.user = self.user
        request.session = {}
        
        response = test_view(request, community_id=self.community.id)
        # Should be a redirect (302) to dashboard because it's not AJAX
        self.assertEqual(response.status_code, 302)
        self.assertTrue(request.session.get('rbac_unauthorized'))

    def test_rbac_decorator_ajax_unauthorized(self):
        # Assign Secretary role
        CommunitySpaceMembership.objects.create(
            community_space=self.space,
            user=self.user,
            role=CommunitySpaceRole.SECRETARY
        )
        
        # Try to access loans via AJAX
        @rbac_permission_required('loans')
        def test_view(request, community_id):
            return JsonResponse({'success': True})
            
        request = self.factory.get(f'/admin/{self.community.id}/api/loans/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.user
        request.session = {}
        
        response = test_view(request, community_id=self.community.id)
        self.assertEqual(response.status_code, 403)
        self.assertIn("can't access this feature", response.content.decode())
