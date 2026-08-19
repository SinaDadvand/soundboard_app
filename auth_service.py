"""
Authentication & Authorization Service for Virtual Soundboard
============================================================
- Google Sign-In verification via Firebase Authentication (firebase-admin)
- Role-Based Access Control (RBAC) via Google Cloud Identity API (Google Groups)
- High-performance in-memory TTL caching for instant soundboard responsiveness
- Seamless local development bypass (DISABLE_AUTH=true)
"""

import os
import time
import functools
import logging
from flask import request, jsonify, g

try:
    from cachetools import TTLCache
except (ImportError, Exception):
    class TTLCache(dict):
        """Lightweight fallback in-memory TTL Cache."""
        def __init__(self, maxsize=1000, ttl=300):
            super().__init__()
            self._ttl = ttl
            self._times = {}

        def __setitem__(self, key, value):
            self._times[key] = time.time()
            super().__setitem__(key, value)

        def __getitem__(self, key):
            if key in self and time.time() - self._times.get(key, 0) < self._ttl:
                return super().__getitem__(key)
            self.pop(key, None)
            self._times.pop(key, None)
            raise KeyError(key)

        def __contains__(self, key):
            if super().__contains__(key) and time.time() - self._times.get(key, 0) < self._ttl:
                return True
            self.pop(key, None)
            self._times.pop(key, None)
            return False

# Configure logger
logger = logging.getLogger('auth_service')
logger.setLevel(logging.INFO)

# Optional Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    from firebase_admin import credentials
    FIREBASE_ADMIN_AVAILABLE = True
except (ImportError, Exception) as e:
    firebase_admin = None
    firebase_auth = None
    FIREBASE_ADMIN_AVAILABLE = False
    logger.warning(f"[AuthService] firebase-admin not installed: {e}")

# Optional Google Cloud Identity API
try:
    from googleapiclient.discovery import build as google_api_build
    import google.auth
    CLOUD_IDENTITY_AVAILABLE = True
except (ImportError, Exception) as e:
    google_api_build = None
    CLOUD_IDENTITY_AVAILABLE = False
    logger.warning(f"[AuthService] google-api-python-client not installed: {e}")


class AuthService:
    def __init__(self):
        self.project_id = os.environ.get('FIREBASE_PROJECT_ID') or os.environ.get('GCP_PROJECT') or os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.allowed_group = os.environ.get('ALLOWED_USER_GROUP')
        self.disable_auth = os.environ.get('DISABLE_AUTH', '').lower() in ('true', '1', 'yes')

        # In-memory TTL caches:
        # Group name lookup: cached for 1 hour
        self._group_name_cache = TTLCache(maxsize=100, ttl=3600)
        # User membership result: cached for 5 minutes (300 seconds)
        self._membership_cache = TTLCache(maxsize=5000, ttl=300)

        self._firebase_initialized = False
        self._cloud_identity_client = None

        self._init_firebase()
        self._init_cloud_identity()

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

    def _init_cloud_identity(self):
        """Initialize Google Cloud Identity v1 API client."""
        if not CLOUD_IDENTITY_AVAILABLE or self.disable_auth:
            return

        try:
            creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-identity.groups.readonly'])
            self._cloud_identity_client = google_api_build('cloudidentity', 'v1', credentials=creds, cache_discovery=False)
            logger.info("[AuthService] Cloud Identity API client initialized successfully.")
        except Exception as e:
            try:
                # Fallback with default discovery
                creds, _ = google.auth.default()
                self._cloud_identity_client = google_api_build('cloudidentity', 'v1', credentials=creds, cache_discovery=False)
                logger.info("[AuthService] Cloud Identity API client initialized with default credentials.")
            except Exception as e2:
                logger.warning(f"[AuthService] Could not initialize Cloud Identity client: {e2}")
                self._cloud_identity_client = None

    def get_group_resource_name(self, group_email: str) -> str:
        """Lookup Cloud Identity group resource name (e.g., 'groups/0123456789') by group email."""
        if not group_email:
            return None

        clean_email = group_email.strip().lower()
        if clean_email in self._group_name_cache:
            return self._group_name_cache[clean_email]

        if not self._cloud_identity_client:
            return None

        try:
            req = self._cloud_identity_client.groups().lookup(groupKey_id=clean_email)
            res = req.execute()
            group_name = res.get('name')
            if group_name:
                self._group_name_cache[clean_email] = group_name
                return group_name
        except Exception as e:
            logger.error(f"[AuthService] Error looking up Cloud Identity group '{clean_email}': {e}")

        return None

    def check_group_membership(self, user_email: str, group_email: str = None) -> bool:
        """Check if user is a direct or indirect (transitive) member of the designated Google Group."""
        target_group = group_email or self.allowed_group
        if not target_group:
            # If no group restriction is configured, allow all authenticated users
            return True

        if not user_email:
            return False

        clean_user = user_email.strip().lower()
        clean_group = target_group.strip().lower()
        cache_key = f"{clean_user}:{clean_group}"

        if cache_key in self._membership_cache:
            return self._membership_cache[cache_key]

        if not self._cloud_identity_client:
            logger.warning("[AuthService] Cloud Identity API client not active. Rejecting group check.")
            return False

        group_resource = self.get_group_resource_name(clean_group)
        if not group_resource:
            logger.error(f"[AuthService] Could not resolve group resource name for '{clean_group}'.")
            return False

        try:
            req = self._cloud_identity_client.groups().memberships().checkTransitiveMembership(
                parent=group_resource,
                query=f"member_key_id == '{clean_user}'"
            )
            res = req.execute()
            has_membership = bool(res.get('hasSubmembership', False))
            self._membership_cache[cache_key] = has_membership
            logger.info(f"[AuthService] Group check for '{clean_user}' in '{clean_group}': {has_membership}")
            return has_membership
        except Exception as e:
            logger.error(f"[AuthService] Transitive membership check failed for '{clean_user}': {e}")
            return False

    def verify_token(self, token: str):
        """Verify Firebase ID Token and return decoded payload."""
        if not FIREBASE_ADMIN_AVAILABLE or not self._firebase_initialized:
            raise RuntimeError("Firebase Admin SDK is not initialized")

        return firebase_auth.verify_id_token(token)

    def get_client_config(self):
        """Return public Firebase configuration for client-side Web SDK."""
        return {
            'apiKey': os.environ.get('FIREBASE_API_KEY', ''),
            'authDomain': os.environ.get('FIREBASE_AUTH_DOMAIN', f"{self.project_id}.firebaseapp.com" if self.project_id else ''),
            'projectId': self.project_id or '',
            'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', f"{self.project_id}.appspot.com" if self.project_id else ''),
            'messagingSenderId': os.environ.get('FIREBASE_MESSAGING_SENDER_ID', ''),
            'appId': os.environ.get('FIREBASE_APP_ID', ''),
            'allowedGroup': self.allowed_group or '',
            'authEnabled': not self.disable_auth
        }


# Global AuthService singleton
auth_service = AuthService()


def require_auth(f):
    """Flask route decorator enforcing Firebase ID Token authentication and Google Group RBAC."""
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
        if not user_email:
            return jsonify({
                'status': 'error',
                'error': 'Forbidden',
                'message': 'Authenticated account does not have an associated email address.'
            }), 403

        # Validate Google Group membership
        if auth_service.allowed_group:
            is_authorized = auth_service.check_group_membership(user_email)
            if not is_authorized:
                return jsonify({
                    'status': 'error',
                    'error': 'Forbidden',
                    'message': f'Access Denied: Your account ({user_email}) is not a member of the required group ({auth_service.allowed_group}).'
                }), 403

        g.current_user = decoded_token
        return f(*args, **kwargs)

    return decorated_function
