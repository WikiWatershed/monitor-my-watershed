"""
WSGI config for WebSDL project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os
import crontab_jobs

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "WebSDL.settings.linux_server")

crontab_jobs.start_jobs()

application = get_wsgi_application()
