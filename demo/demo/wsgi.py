import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings_django")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
