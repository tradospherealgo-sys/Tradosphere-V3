"""
WSGI entry point for Render deployment
Imports the Flask app from the backend module
"""

from backend.tradosphere_saas_server_v3_1 import app

if __name__ == '__main__':
    app.run()
