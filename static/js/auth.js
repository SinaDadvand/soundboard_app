/**
 * Firebase Authentication & Google Group RBAC Controller
 * ======================================================
 * - Initializes Firebase Web SDK v10 (compat) dynamically from backend config
 * - Google Sign-In with popup (GoogleAuthProvider)
 * - Transparent Bearer token injection for all API requests (authenticatedFetch)
 * - Real-time auth state handling & 403 Forbidden Access Denied feedback
 */

(function() {
    let authConfig = null;
    let currentUser = null;
    let currentIdToken = null;
    let isAuthInitialized = false;

    // DOM Elements
    let authContainer = null;
    let authLoginBtn = null;
    let authUserProfile = null;
    let authUserAvatar = null;
    let authUserName = null;
    let authSignOutBtn = null;
    let authBarrierModal = null;
    let authForbiddenModal = null;
    let authForbiddenMsg = null;
    let authBarrierLoginBtn = null;
    let authForbiddenSwitchBtn = null;

    function initDOMElements() {
        authContainer = document.getElementById('auth-container');
        authLoginBtn = document.getElementById('auth-login-btn');
        authUserProfile = document.getElementById('auth-user-profile');
        authUserAvatar = document.getElementById('auth-user-avatar');
        authUserName = document.getElementById('auth-user-name');
        authSignOutBtn = document.getElementById('auth-signout-btn');
        authBarrierModal = document.getElementById('auth-barrier-modal');
        authForbiddenModal = document.getElementById('auth-forbidden-modal');
        authForbiddenMsg = document.getElementById('auth-forbidden-msg');
        authBarrierLoginBtn = document.getElementById('auth-barrier-login-btn');
        authForbiddenSwitchBtn = document.getElementById('auth-forbidden-switch-btn');

        if (authLoginBtn) {
            authLoginBtn.addEventListener('click', signInWithGoogle);
        }
        if (authBarrierLoginBtn) {
            authBarrierLoginBtn.addEventListener('click', signInWithGoogle);
        }
        if (authSignOutBtn) {
            authSignOutBtn.addEventListener('click', signOutUser);
        }
        if (authForbiddenSwitchBtn) {
            authForbiddenSwitchBtn.addEventListener('click', async () => {
                await signOutUser();
                await signInWithGoogle();
            });
        }
    }

    async function initAuth() {
        initDOMElements();

        try {
            const res = await fetch('/api/auth/config');
            authConfig = await res.json();

            if (!authConfig.authEnabled || !authConfig.apiKey) {
                console.log('[Auth] Auth is disabled or unconfigured in this environment. Bypassing client login.');
                if (authContainer) authContainer.classList.add('hidden');
                if (authBarrierModal) authBarrierModal.classList.add('hidden');
                window.dispatchEvent(new CustomEvent('auth-state-ready', { detail: { authorized: true, user: null } }));
                return;
            }

            if (typeof firebase === 'undefined') {
                console.error('[Auth] Firebase Web SDK script not loaded.');
                return;
            }

            if (!firebase.apps.length) {
                firebase.initializeApp(authConfig);
            }

            firebase.auth().onAuthStateChanged(handleAuthStateChanged);
            isAuthInitialized = true;
        } catch (err) {
            console.error('[Auth] Failed to initialize Firebase Auth:', err);
        }
    }

    async function handleAuthStateChanged(user) {
        currentUser = user;
        if (user) {
            try {
                currentIdToken = await user.getIdToken();
            } catch (e) {
                console.error('[Auth] Error fetching ID token:', e);
            }

            // Update UI for logged in state
            if (authLoginBtn) authLoginBtn.classList.add('hidden');
            if (authUserProfile) authUserProfile.classList.remove('hidden');
            if (authUserName) authUserName.textContent = user.displayName || user.email.split('@')[0];
            if (authUserAvatar) {
                if (user.photoURL) {
                    authUserAvatar.src = user.photoURL;
                    authUserAvatar.classList.remove('hidden');
                } else {
                    authUserAvatar.classList.add('hidden');
                }
            }

            // Verify authorization with backend
            try {
                const meRes = await fetch('/api/auth/me', {
                    headers: { 'Authorization': `Bearer ${currentIdToken}` }
                });

                if (meRes.status === 403) {
                    const data = await meRes.json();
                    showForbiddenModal(data.message || 'Your account is not authorized to access this application.');
                    return;
                }

                if (meRes.ok) {
                    if (authBarrierModal) authBarrierModal.classList.add('hidden');
                    if (authForbiddenModal) authForbiddenModal.classList.add('hidden');
                    window.dispatchEvent(new CustomEvent('auth-state-ready', { detail: { authorized: true, user: user } }));
                } else {
                    showBarrierModal();
                }
            } catch (err) {
                console.error('[Auth] Error verifying user status:', err);
            }
        } else {
            currentIdToken = null;
            if (authLoginBtn) authLoginBtn.classList.remove('hidden');
            if (authUserProfile) authUserProfile.classList.add('hidden');
            showBarrierModal();
            window.dispatchEvent(new CustomEvent('auth-state-ready', { detail: { authorized: false, user: null } }));
        }
    }

    async function signInWithGoogle() {
        if (!isAuthInitialized) {
            console.warn('[Auth] Firebase not yet initialized.');
            return;
        }

        const provider = new firebase.auth.GoogleAuthProvider();
        provider.setCustomParameters({ prompt: 'select_account' });

        try {
            await firebase.auth().signInWithPopup(provider);
        } catch (err) {
            if (err.code !== 'auth/popup-closed-by-user') {
                console.error('[Auth] Sign in popup error:', err);
                alert(`Sign-in error: ${err.message}`);
            }
        }
    }

    async function signOutUser() {
        if (isAuthInitialized && firebase.auth()) {
            await firebase.auth().signOut();
        }
    }

    function showBarrierModal() {
        if (authBarrierModal) authBarrierModal.classList.remove('hidden');
        if (authForbiddenModal) authForbiddenModal.classList.add('hidden');
    }

    function showForbiddenModal(msg) {
        if (authForbiddenModal) authForbiddenModal.classList.remove('hidden');
        if (authBarrierModal) authBarrierModal.classList.add('hidden');
        if (authForbiddenMsg) {
            authForbiddenMsg.textContent = msg;
        }
    }

    /**
     * Globally accessible fetch wrapper that automatically appends the Bearer token
     * and catches 401 Unauthorized / 403 Forbidden responses.
     */
    window.authenticatedFetch = async function(url, options = {}) {
        options.headers = options.headers || {};

        if (currentUser) {
            try {
                // Ensure fresh ID token
                currentIdToken = await currentUser.getIdToken();
                if (options.headers instanceof Headers) {
                    options.headers.set('Authorization', `Bearer ${currentIdToken}`);
                } else {
                    options.headers['Authorization'] = `Bearer ${currentIdToken}`;
                }
            } catch (e) {
                console.error('[Auth] Could not retrieve fresh token:', e);
            }
        }

        const response = await fetch(url, options);

        if (response.status === 401) {
            console.warn('[Auth] Received 401 Unauthorized from backend.');
            showBarrierModal();
        } else if (response.status === 403) {
            console.warn('[Auth] Received 403 Forbidden from backend.');
            try {
                const errData = await response.clone().json();
                showForbiddenModal(errData.message || 'Access Denied: Your account is not authorized to access this application.');
            } catch (e) {
                showForbiddenModal('Access Denied: Your account is not authorized to access this application.');
            }
        }

        return response;
    };

    // Export helpers to global scope
    window.soundboardAuth = {
        signInWithGoogle,
        signOut: signOutUser,
        getUser: () => currentUser,
        getToken: () => currentIdToken
    };

    document.addEventListener('DOMContentLoaded', initAuth);
})();
