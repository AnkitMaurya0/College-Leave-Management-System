# This file contains the database models for the Leave Management System
# The actual database operations are handled directly in app.py using PostgreSQL

class User:
    """User model representing students and admins"""
    def __init__(self, id, username, email, password_hash, role, created_at):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role  # 'student' or 'admin'
        self.created_at = created_at

class Leave:
    """Leave model representing leave applications"""
    def __init__(self, id, user_id, from_date, to_date, reason, status, admin_comments, applied_at, updated_at):
        self.id = id
        self.user_id = user_id
        self.from_date = from_date
        self.to_date = to_date
        self.reason = reason
        self.status = status  # 'pending', 'approved', 'rejected'
        self.admin_comments = admin_comments
        self.applied_at = applied_at
        self.updated_at = updated_at