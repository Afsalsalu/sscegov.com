# timezone_test.py
from django.utils import timezone

# Convert UTC datetime to IST
utc_datetime = timezone.now()
ist_datetime = utc_datetime.astimezone(timezone.get_current_timezone())

# Display IST datetime
print(ist_datetime)
