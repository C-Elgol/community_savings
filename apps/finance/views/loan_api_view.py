from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from apps.finance.models import LoanApplication, Loan, LoanProduct, FinancialSeason, Membership
from apps.global_data.enum import LoanApplicationStatus
import json
from django.db import transaction
from django.utils import timezone

class LoanApplicationAPI(View):
    def get(self, request, community_id):
        status = request.GET.get('status')
        filters = {'membership__community_id': community_id}
        if status:
            filters['status'] = status
        
        apps = LoanApplication.objects.filter(**filters).select_related('membership__user', 'loan_product', 'season').order_by('-created')
        
        data = []
        for a in apps:
            data.append({
                'id': str(a.id),
                'member_name': a.membership.user.get_full_name or a.membership.user.username,
                'amount_requested': str(a.amount_requested),
                'product_name': a.loan_product.name,
                'term_months': a.proposed_term_months,
                'status': a.status,
                'submitted_at': a.created.isoformat(),
                'purpose': a.purpose,
                'season_title': a.season.title if a.season else '---'
            })
        
        return JsonResponse({'success': True, 'applications': data})

    def post(self, request, community_id):
        try:
            data = json.loads(request.body)
            membership_id = data.get('membership_id')
            product_id = data.get('product_id')
            season_id = data.get('season_id')
            signature = data.get('signature_data')
            frequency = data.get('repayment_frequency', 'monthly')
            
            # If membership_id is missing, assume it's the current user applying
            if not membership_id:
                membership = Membership.objects.filter(user=request.user, community_id=community_id, status='active').first()
                if not membership:
                    return JsonResponse({'success': False, 'message': 'Active membership not found'}, status=404)
            else:
                membership = get_object_or_404(Membership, id=membership_id)
            
            # If season_id is missing, use the active season for the community
            if not season_id:
                season = FinancialSeason.objects.filter(community_id=community_id, is_closed=False).first()
            else:
                season = FinancialSeason.objects.filter(id=season_id).first()
            
            product = get_object_or_404(LoanProduct, id=product_id)
            
            loan_app = LoanApplication.objects.create(
                membership=membership,
                loan_product=product,
                season=season,
                amount_requested=data.get('amount_requested'),
                proposed_term_months=data.get('term_months'),
                repayment_frequency=frequency,
                purpose=data.get('purpose', ''),
                signature_data=signature,
                status=LoanApplicationStatus.SUBMITTED,
                submitted_at=timezone.now()
            )
            
            return JsonResponse({'success': True, 'message': 'Loan application submitted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    def patch(self, request, application_id):
        try:
            data = json.loads(request.body)
            action = data.get('action') # 'approve' or 'reject'
            loan_app = get_object_or_404(LoanApplication, id=application_id)
            
            if action == 'approve':
                with transaction.atomic():
                    loan_app.status = LoanApplicationStatus.APPROVED
                    loan_app.save()
                    
                    # Create the actual loan
                    Loan.objects.create(
                        application=loan_app,
                        membership=loan_app.membership,
                        season=loan_app.season,
                        amount_borrowed=loan_app.amount_requested,
                        interest_to_be_paid=(loan_app.amount_requested * loan_app.loan_product.interest_rate) / 100,
                        borrow_date=timezone.now().date(),
                        repayment_frequency=loan_app.repayment_frequency,
                        status='active'
                    )
                return JsonResponse({'success': True, 'message': 'Loan application approved and loan created'})
            
            elif action == 'reject':
                loan_app.status = LoanApplicationStatus.REJECTED
                loan_app.rejection_reason = data.get('reason', 'Rejected by administrator')
                loan_app.save()
                return JsonResponse({'success': True, 'message': 'Loan application rejected'})
            
            return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

class LoanAPI(View):
    def get(self, request, community_id):
        status = request.GET.get('status')
        filters = {'membership__community_id': community_id}
        if status:
            filters['status'] = status
            
        loans = Loan.objects.filter(**filters).select_related('membership__user', 'application__loan_product').order_by('-borrow_date')
        
        data = []
        for l in loans:
            data.append({
                'id': str(l.id),
                'member_name': l.membership.user.get_full_name or l.membership.user.username,
                'amount_borrowed': str(l.amount_borrowed),
                'amount_paid': str(l.amount_paid),
                'interest': str(l.interest_to_be_paid),
                'total_amount': str(l.total_amount_plus_interest),
                'borrow_date': l.borrow_date.isoformat(),
                'maturity_date': l.maturity_date.isoformat() if l.maturity_date else None,
                'status': l.status,
                'product_name': l.application.loan_product.name if l.application else '---'
            })
            
        return JsonResponse({'success': True, 'loans': data})

class LoanProductAPI(View):
    def get(self, request, community_id):
        products = LoanProduct.objects.filter(community_id=community_id, is_active=True).values('id', 'name', 'min_amount', 'max_amount', 'interest_rate')
        return JsonResponse({'success': True, 'products': list(products)})

class MembershipAPI(View):
    def get(self, request, community_id):
        members = Membership.objects.filter(community_id=community_id, status='active').values('id', 'user__first_name', 'user__last_name', 'user__email')
        data = []
        for m in members:
            data.append({
                'id': str(m['id']),
                'name': f"{m['user__first_name']} {m['user__last_name']}" if m['user__first_name'] else m['user__email']
            })
        return JsonResponse({'success': True, 'members': data})
