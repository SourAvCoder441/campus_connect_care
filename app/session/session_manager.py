# app/session/session_manager.py

class SessionManager:
    """Manages the current user session"""
    
    _instance = None
    _current_user = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def login(self, user_id, username, role):
        """Set current user on successful login"""
        self._current_user = {
            'id': user_id,
            'username': username,
            'role': role,
            'logged_in_at': __import__('datetime').datetime.now().isoformat()
        }
        return True
    
    def logout(self):
        """Clear current user on logout"""
        self._current_user = None
        return True
    
    def get_current_user(self):
        """Get the currently logged in user"""
        return self._current_user
    
    def is_authenticated(self):
        """Check if a user is logged in"""
        return self._current_user is not None
    
    def has_role(self, role):
        """Check if current user has a specific role"""
        return self._current_user and self._current_user.get('role') == role


# Create a single instance (singleton)
session = SessionManager()

# Convenience functions
def get_current_user():
    """Get the current logged in user"""
    return session.get_current_user()

def set_current_user(user_id, username, role):
    """Set the current user (called after login)"""
    return session.login(user_id, username, role)

def logout_current_user():
    """Log out the current user"""
    return session.logout()
