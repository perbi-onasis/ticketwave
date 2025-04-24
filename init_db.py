from src import create_app, db
from src.models.user import User
from src.models.event import Event, TicketType, Promotion
from src.models.ticket import Ticket
from werkzeug.security import generate_password_hash
from datetime import datetime

def init_db():
    app = create_app()
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            role='admin',
            is_promoter=False,
            is_verified=True
        )
        db.session.add(admin)
        
        # Create a test promoter
        promoter = User(
            username='testpromoter',
            email='promoter@example.com',
            password=generate_password_hash('promoter123'),
            role='promoter',
            is_promoter=True,
            is_verified=True
        )
        db.session.add(promoter)
        
        try:
            db.session.commit()
            print("Database initialized successfully!")
            print("\nTest accounts created:")
            print("Admin - Email: admin@example.com, Password: admin123")
            print("Promoter - Email: promoter@example.com, Password: promoter123")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    init_db() 