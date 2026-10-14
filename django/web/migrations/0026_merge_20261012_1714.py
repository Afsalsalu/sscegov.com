"""Compatibility node for the migration already applied in production.

The production server created and applied this merge migration before the
Annual KYC work was added.  Keep its migration identity in source control so
future migrations have the same graph on fresh databases and on production.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0025_franchiseenquiry_related_service"),
    ]

    operations = []
