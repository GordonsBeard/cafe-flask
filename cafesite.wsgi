import logging, os, sys

sys.path.insert(0, '/var/www/cafeofbrokendreams.com/cafe-flask')
os.chdir('/var/www/cafeofbrokendreams.com/cafe-flask')

logging.basicConfig(stream=sys.stderr)

from cafesite import app as application
