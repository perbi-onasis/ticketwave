from src.models import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='promoter')  # 'admin', 'promoter'
    is_promoter = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True, nullable=True)

    # Define relationships
    events = db.relationship('Event', 
                           backref='promoter_user',
                           lazy=True,
                           foreign_keys='Event.promoter')
    tickets = db.relationship('Ticket', 
                            back_populates='user',
                            foreign_keys='Ticket.user_id')

    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_active(self):
        # Promoters need verification, customers don't
        if self.role == 'promoter':
            return self.is_verified
        return True

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        if not self.password:
            return False
        return check_password_hash(self.password, password)

    def generate_verification_token(self):
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token