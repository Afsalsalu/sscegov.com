import logging
import os

import django
from django.apps import apps


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ssc.settings")

logger = logging.getLogger(__name__)

def test_smtp_connection():
    if not apps.ready:
        django.setup()
    from django.core.mail import get_connection

    connection = get_connection(fail_silently=False)
    try:
        connection.open()
        print("Configured Django email backend opened successfully.")
    except Exception:
        logger.exception("Could not open the configured Django email backend.")
        print("Could not connect to the configured email backend. See the server log.")
    finally:
        connection.close()

if __name__ == "__main__":
    test_smtp_connection()

