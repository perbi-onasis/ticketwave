from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from src.config import Config
from src.models import db
from src.utils.email import mail
from datetime import datetime
import os

login_manager = LoginManager()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Create upload directories
    uploads_dir = os.path.join(app.static_folder, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = uploads_dir

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db, directory='migrations')
    mail.init_app(app)

    # Add user loader
    @login_manager.user_loader
    def load_user(user_id):
        from src.models.user import User
        return User.query.get(int(user_id))

    # Set login view
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Add context processor for global template variables
    @app.context_processor
    def inject_categories():
        from src.models.event import EVENT_CATEGORIES
        from main import CATEGORY_ICONS
        return dict(
            categories=EVENT_CATEGORIES,
            category_icons=CATEGORY_ICONS,
            current_year=datetime.now().year
        )

    # Register blueprints
    from src.routes.auth import auth
    from src.routes.admin import admin
    from src.routes.user import user
    from src.routes.promoter import promoter
    from main import main
    
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(user)
    app.register_blueprint(promoter)

    return app
