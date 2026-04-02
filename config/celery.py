# medicine_reminder/celery.py
import os
from celery import Celery
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Load Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Explicitly discover tasks in the tasks subpackage
app.autodiscover_tasks([
    'apps.users.tasks',
    'apps.log.tasks',
    'apps.communities.tasks',
    'apps.finance.tasks',
])

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')