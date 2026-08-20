"""
Authentication & Authorization Service for Virtual Soundboard
============================================================
- Google Sign-In verification via Firebase Authentication (firebase-admin)
- Email allowlist Role-Based Access Control via ALLOWED_USERS env variable
- Seamless local development bypass (DISABLE_AUTH=true)
"""

import os
import functools
import logging
from flask import request, jsonify, g

# Configure logger
logger = logging.getLogger('auth_service')
logger.setLevel(logging.INFO)

# Optional Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    FIREBASE_ADMIN_AVAILABLE = True
except (ImportError, Exception) as e:
    firebase_admin = None
    firebase_auth = None
    FIREBASE_ADMIN_AVAILABLE = False
    logger.warning(f"[AuthService] firebase-admin not installed: {e}")


class AuthService:
    def __init__(self):
        self.project_id = os.environ.get('FIREBASE_PROJECT_ID') or os.environ.get('GCP_PROJECT') or os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.disable_auth = os.environ.get('DISABLE_AUTH', '').lower() in ('true', '1', 'yes')

        # Parse ALLOWED_USERS environment variable on startup into a normalized, trimmed list of lowercased emails
        raw_allowed = os.environ.get('ALLOWED_USERS', '')
        self.allowed_users = set(
            email.strip().lower()
            for email in raw_allowed.split(',')
            if email.strip()
        )
        logger.info(f"[AuthService] Initialized with {len(self.allowed_users)} authorized email(s).")

        self.allowed_group = None
        self._firebase_initialized = False
        self._init_firebase()

    def _init_firebase(self):
        """Initialize Firebase Admin SDK using Application Default Credentials (ADC)."""
        if not FIREBASE_ADMIN_AVAILABLE or self.disable_auth:
            return

        if not firebase_admin._apps:
            try:
                if self.project_id:
                    firebase_admin.initialize_app(options={'projectId': self.project_id})
                else:
                    firebase_admin.initialize_app()
                self._firebase_initialized = True
                logger.info(f"[AuthService] Firebase Admin SDK initialized successfully (Project: {self.project_id or 'default'}).")
            except Exception as e:
                logger.warning(f"[AuthService] Could not initialize Firebase Admin SDK: {e}")
                self._firebase_initialized = False
        else:
            self._firebase_initialized = True

    def is_user_authorized(self, email: str) -> bool:
        """Check if email is in the allowed users list."""
        if not self.allowed_users:
            # If no email allowlist is configured, allow all authenticated users
            return True

        if not email:
            return False

        normalized_email = email.strip().lower()
        return normalized_email in self.allowed_users

    def verify_token(self, token: str):
        """Verify Firebase ID Token and return decoded payload."""
        if not FIREBASE_ADMIN_AVAILABLE or not self._firebase_initialized:
            raise RuntimeError("Firebase Admin SDK is not initialized")

        return firebase_auth.verify_id_token(token)

    def get_client_config(self):
        """Return public Firebase configuration for client-side Web SDK."""
        api_key = (
            os.environ.get('FIREBASE_API_KEY') or 
            os.environ.get('FIREBASE_WEB_API_KEY') or 
            os.environ.get('GOOGLE_API_KEY') or 
            os.environ.get('GCP_API_KEY') or 
            ''
        )
        project_id = (
            self.project_id or 
            os.environ.get('GCP_PROJECT') or 
            os.environ.get('GOOGLE_CLOUD_PROJECT') or 
            'p-np-adt-de'
        )
        auth_domain = (
            os.environ.get('FIREBASE_AUTH_DOMAIN') or 
            f"{project_id}.firebaseapp.com"
        )
        storage_bucket = (
            os.environ.get('FIREBASE_STORAGE_BUCKET') or 
            f"{project_id}.appspot.com"
        )
        return {
            'apiKey': api_key,
            'authDomain': auth_domain,
            'projectId': project_id,
            'storageBucket': storage_bucket,
            'messagingSenderId': os.environ.get('FIREBASE_MESSAGING_SENDER_ID', ''),
            'appId': os.environ.get('FIREBASE_APP_ID', ''),
            'authEnabled': not self.disable_auth
        }


# Global AuthService singleton
auth_service = AuthService()


def require_auth(f):
    """Flask route decorator enforcing Firebase ID Token authentication and ALLOWED_USERS email authorization."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if auth_service.disable_auth:
            # Mock authenticated user for offline / desktop development
            g.current_user = {
                'uid': 'local-dev-user',
                'email': 'developer@local.test',
                'name': 'Local Developer'
            }
            return f(*args, **kwargs)

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'status': 'error',
                'error': 'Unauthorized',
                'message': 'Missing or invalid Authorization header. Please sign in with Google.'
            }), 401

        token = auth_header.split('Bearer ', 1)[1].strip()
        if not token:
            return jsonify({
                'status': 'error',
                'error': 'Unauthorized',
                'message': 'Bearer token is empty.'
            }), 401

        try:
            decoded_token = auth_service.verify_token(token)
        except Exception as e:
            logger.warning(f"[AuthService] Token verification error: {e}")
            return jsonify({
                'status': 'error',
                'error': 'Unauthorized',
                'message': f'Invalid or expired session token: {e}'
            }), 401

        user_email = decoded_token.get('email')
        if not user_email or not auth_service.is_user_authorized(user_email):
            return jsonify({
                'status': 'error',
                'error': 'Access Denied: Your account is not authorized to access this application.',
                'message': 'Access Denied: Your account is not authorized to access this application.'
            }), 403

        g.current_user = decoded_token
        return f(*args, **kwargs)

    return decorated_function
