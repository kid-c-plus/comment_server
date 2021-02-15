import sys, os
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from app import flaskapp
flaskapp.run(host="0.0.0.0", port=5000, use_reloader=False)
