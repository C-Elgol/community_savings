import os
import django
import random
from decimal import Decimal
from datetime import date, timedelta, datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.communities.models import Community, Membership, CommunityFeature, MemberFeatureParticipation
from apps.finance.models import (
    FinancialSeason, ContributionCycle, Contribution, Loan, 
    LoanRepaymentSchedule, LoanPayment, Fine, LoanProduct,
    LoanApplication
)
from apps.meetings.models import Meeting, MeetingAttendance, MeetingMinute
from apps.global_data.enum import (
    ContributionStatus, LoanStatus, LoanApplicationStatus, 
    FineType, FineStatus, CommunityFeatureType, MinuteStatus,
    MembershipRole, MembershipStatus
)
from django.contrib.auth import get_user_model

User = get_user_model()

def populate_data():
    community_name = "Mouckbie Teachers Association (MOTA)"
    try:
        community = Community.objects.get(name=community_name)
    except Community.DoesNotExist:
        print(f"Community {community_name} not found.")
        return

    print(f"Targeting Community: {community.name}")

    # 1. Ensure Features are enabled
    features = [
        CommunityFeatureType.SAVINGS,
        CommunityFeatureType.LOANS,
        CommunityFeatureType.NJANGI,
        CommunityFeatureType.ENTERTAINMENT,
        CommunityFeatureType.PROJECT,
        CommunityFeatureType.EVENTS,
        CommunityFeatureType.SINKING_FUND,
    ]
    for fetch_type in features:
        CommunityFeature.objects.get_or_create(community=community, feature_type=fetch_type, defaults={'is_active': True})

    # 2. Get active members
    memberships = Membership.objects.filter(community=community, status='active')
    if not memberships.exists():
        print("No active members found.")
        return

    # Ensure all members participate in all features
    for m in memberships:
        for fetch_type in features:
            feature = CommunityFeature.objects.get(community=community, feature_type=fetch_type)
            MemberFeatureParticipation.objects.get_or_create(membership=m, feature=feature, defaults={'is_active': True})

    # 3. Handle Seasons
    seasons_data = [
        {"title": "2026 season", "date": date(2026, 4, 16)},
        {"title": "2027 season", "date": date(2027, 4, 16)}
    ]

    loan_product = LoanProduct.objects.filter(community=community).first()

    current_date = date(2026, 4, 16)

    for season_info in seasons_data:
        season, created = FinancialSeason.objects.get_or_create(
            community=community,
            season_date=season_info["date"],
            defaults={"title": season_info["title"]}
        )
        print(f"Processing Season: {season.title} (Created: {created})")

        # Generate 12 cycles for each season
        for i in range(12):
            cycle_date = season_info["date"] + timedelta(days=30 * i)
            cycle_title = f"Cycle {i+1} - {season.title}"
            
            cycle, created = ContributionCycle.objects.get_or_create(
                community=community,
                season=season,
                due_date=cycle_date,
                defaults={
                    "title": cycle_title,
                    "expected_amount": Decimal("10000.00"),
                    "is_closed": True
                }
            )
            
            # Create Meeting
            meeting, created = Meeting.objects.get_or_create(
                community=community,
                scheduled_date=cycle_date,
                defaults={
                    "title": f"Meeting for {cycle_title}",
                    "start_time": "14:00:00",
                    "end_time": "16:00:00",
                    "venue": "Community Hall",
                    "is_closed": True
                }
            )
            
            # Meeting Attendance
            for m in memberships:
                is_present = random.random() > 0.1
                is_late = is_present and random.random() > 0.8
                MeetingAttendance.objects.get_or_create(
                    meeting=meeting,
                    membership=m,
                    defaults={
                        "was_present": is_present,
                        "arrived_late": is_late,
                        "remarks": "Standard attendance" if is_present else "Absent"
                    }
                )
                
                # Fines for absence/lateness
                if not is_present:
                    Fine.objects.get_or_create(
                        membership=m,
                        season=season,
                        fine_type=FineType.ABSENCE,
                        issued_date=cycle_date,
                        defaults={
                            "amount": Decimal("1000.00"),
                            "reason": "Absent from meeting",
                            "status": FineStatus.PAID if random.random() > 0.3 else FineStatus.UNPAID
                        }
                    )
                elif is_late:
                    Fine.objects.get_or_create(
                        membership=m,
                        season=season,
                        fine_type=FineType.MANUAL,
                        issued_date=cycle_date,
                        defaults={
                            "amount": Decimal("500.00"),
                            "reason": "Late for meeting",
                            "status": FineStatus.PAID if random.random() > 0.2 else FineStatus.UNPAID
                        }
                    )

            # Contributions
            for m in memberships:
                # Primary Savings Contribution
                Contribution.objects.get_or_create(
                    membership=m,
                    cycle=cycle,
                    feature_type=CommunityFeatureType.SAVINGS,
                    defaults={
                        "expected_amount": Decimal("10000.00"),
                        "amount_paid": Decimal("10000.00") if random.random() > 0.05 else Decimal("0.00"),
                        "status": ContributionStatus.PAID if random.random() > 0.05 else ContributionStatus.PENDING,
                        "paid_at": timezone.make_aware(datetime.combine(cycle_date, datetime.min.time()))
                    }
                )
                
                # Njangi Contribution
                Contribution.objects.get_or_create(
                    membership=m,
                    cycle=cycle,
                    feature_type=CommunityFeatureType.NJANGI,
                    defaults={
                        "expected_amount": Decimal("5000.00"),
                        "amount_paid": Decimal("5000.00") if random.random() > 0.1 else Decimal("0.00"),
                        "status": ContributionStatus.PAID if random.random() > 0.1 else ContributionStatus.PENDING,
                        "paid_at": timezone.make_aware(datetime.combine(cycle_date, datetime.min.time()))
                    }
                )

            # Meeting Minutes
            MeetingMinute.objects.get_or_create(
                meeting=meeting,
                defaults={
                    "title": f"Minutes for {cycle_title}",
                    "minute_date": cycle_date,
                    "start_time": "14:00:00",
                    "end_time": "16:00:00",
                    "prepared_by": community.created_by or memberships[0].user,
                    "opening_remarks": "The meeting started at 2 PM as scheduled.",
                    "agenda_summary": "1. Savings Review\n2. Loan Applications\n3. Njangi Distribution",
                    "discussions": "The group discussed the importance of consistent savings.",
                    "decisions": "All pending loan applications were reviewed.",
                    "status": MinuteStatus.FINAL
                }
            )

            # Loans (Occasionally)
            if i % 3 == 0 and loan_product:
                # Pick a random member who hasn't defaulted recently (ignore for simulation)
                borrower = random.choice(memberships)
                loan_amount = Decimal(random.randint(50000, 200000))
                
                # Application
                application = LoanApplication.objects.create(
                    membership=borrower,
                    loan_product=loan_product,
                    season=season,
                    amount_requested=loan_amount,
                    proposed_term_months=6,
                    status=LoanApplicationStatus.APPROVED,
                    submitted_at=timezone.make_aware(datetime.combine(cycle_date, datetime.min.time())),
                    decision_at=timezone.make_aware(datetime.combine(cycle_date, datetime.min.time()))
                )
                
                # Loan
                loan = Loan.objects.create(
                    application=application,
                    membership=borrower,
                    season=season,
                    amount_borrowed=loan_amount,
                    interest_to_be_paid=loan_amount * Decimal("0.10"),
                    borrow_date=cycle_date,
                    status=LoanStatus.ACTIVE if i < 9 else LoanStatus.PAID
                )
                
                # Schedule
                for month in range(1, 7):
                    due_date = cycle_date + timedelta(days=30 * month)
                    is_paid = due_date < date.today() and random.random() > 0.1
                    LoanRepaymentSchedule.objects.create(
                        loan=loan,
                        installment_number=month,
                        due_date=due_date,
                        amount_due=(loan_amount * Decimal("1.10")) / 6,
                        amount_paid=(loan_amount * Decimal("1.10")) / 6 if is_paid else 0,
                        is_paid=is_paid
                    )
                    
                    if is_paid:
                        LoanPayment.objects.create(
                            loan=loan,
                            season=season,
                            amount=(loan_amount * Decimal("1.10")) / 6,
                            payment_date=due_date
                        )

    print("Data population complete!")

if __name__ == "__main__":
    populate_data()
