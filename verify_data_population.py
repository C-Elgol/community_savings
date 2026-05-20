import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.communities.models import Community
from apps.finance.models import FinancialSeason, ContributionCycle, Contribution, Loan, LoanPenalty, Fine
from apps.meetings.models import Meeting, MeetingAttendance, MeetingMinute

def verify_data():
    community_name = "Mouckbie Teachers Association (MOTA)"
    try:
        community = Community.objects.get(name=community_name)
    except Community.DoesNotExist:
        print(f"Community {community_name} not found.")
        return

    print(f"--- Verification for Community: {community.name} ---")
    
    seasons = FinancialSeason.objects.filter(community=community)
    print(f"Seasons: {seasons.count()}")
    for s in seasons:
        cycles = ContributionCycle.objects.filter(season=s)
        print(f"  Season {s.title}: {cycles.count()} cycles")
        
    meetings = Meeting.objects.filter(community=community)
    print(f"Total Meetings: {meetings.count()}")
    
    attendance = MeetingAttendance.objects.filter(meeting__community=community)
    print(f"Total Attendance Records: {attendance.count()}")
    
    minutes = MeetingMinute.objects.filter(meeting__community=community)
    print(f"Total Meeting Minutes: {minutes.count()}")
    
    contributions = Contribution.objects.filter(membership__community=community)
    print(f"Total Contributions: {contributions.count()}")
    
    loans = Loan.objects.filter(membership__community=community)
    print(f"Total Loans: {loans.count()}")
    
    fines = Fine.objects.filter(membership__community=community)
    print(f"Total Fines: {fines.count()}")

    print("\nVerification Complete!")

if __name__ == "__main__":
    verify_data()
