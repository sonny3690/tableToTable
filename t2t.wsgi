import os, sys, logging

os.chdir('/home/t2t/public_html/routes')
sys.path.insert(0, '/home/t2t/public_html/routes')
sys.stdout = sys.stderr
logging.basicConfig(stream=sys.stderr)

from t2t import app as application

