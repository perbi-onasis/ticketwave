from flask import Blueprint, render_template, redirect, url_for, request, flash
from src.models.event import Event, EVENT_CATEGORIES
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

main = Blueprint('main', __name__)
db = SQLAlchemy()

# Add this dictionary to map categories to their icons
CATEGORY_ICONS = {
    'all_events': 'fas fa-calendar',
    'nightlife_parties': 'fas fa-moon',
    'movies_cinema': 'fas fa-film',
    'arts_theatre': 'fas fa-theater-masks',
    'food_drinks': 'fas fa-utensils',
    'networking': 'fas fa-handshake',
    'travel_outdoor': 'fas fa-hiking',
    'professional': 'fas fa-briefcase',
    'health_wellness': 'fas fa-heartbeat',
    'family_education': 'fas fa-graduation-cap',
    'charity_causes': 'fas fa-hand-holding-heart',
    'science_technology': 'fas fa-microscope',
    'religion_spirituality': 'fas fa-pray',
    'community_culture': 'fas fa-users',
    'fashion': 'fas fa-tshirt',
    'esports': 'fas fa-gamepad',
    'sports': 'fas fa-running',
    'other': 'fas fa-ellipsis-h'
}

@main.route('/')
def index():
    try:
        # Get featured events
        featured_events = Event.query.filter(
            Event.date >= datetime.now(),
            Event.status == 'approved',
            Event.is_featured == True
        ).order_by(Event.date).limit(6).all()

        # Get upcoming events
        upcoming_events = Event.query.filter(
            Event.date >= datetime.now(),
            Event.status == 'approved'
        ).order_by(Event.date).limit(8).all()

        # Group events by category
        events_by_category = {}
        for category in EVENT_CATEGORIES:
            category_events = Event.query.filter(
                Event.date >= datetime.now(),
                Event.status == 'approved',
                Event.category == category
            ).order_by(Event.date).limit(4).all()
            
            if category_events:  # Only add categories that have events
                events_by_category[category] = category_events

        return render_template('index.html',
                             featured_events=featured_events,
                             upcoming_events=upcoming_events,
                             events_by_category=events_by_category,
                             categories=EVENT_CATEGORIES,
                             category_icons=CATEGORY_ICONS,
                             current_year=datetime.now().year)

    except Exception as e:
        print(f"Error in index route: {str(e)}")
        flash('An error occurred while loading events. Please try again.', 'danger')
        return render_template('index.html',
                             featured_events=[],
                             upcoming_events=[],
                             events_by_category={},
                             categories=EVENT_CATEGORIES,
                             category_icons=CATEGORY_ICONS,
                             current_year=datetime.now().year)

@main.route('/events')
def events():
    try:
        category = request.args.get('category')
        search = request.args.get('q')
        date_filter = request.args.get('date')
        price_filter = request.args.get('price')
        sort_by = request.args.get('sort', 'date')
        
        # Base query for active events
        query = Event.query.filter(
            Event.date >= datetime.now(),
            Event.status == 'approved'
        )
        
        # Apply category filter
        if category and category != 'all_events':
            query = query.filter(Event.category == category)
            
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Event.name.ilike(search_term),
                    Event.description.ilike(search_term),
                    Event.venue.ilike(search_term)
                )
            )
            
        # Apply sorting
        if sort_by == 'date':
            query = query.order_by(Event.date)
        elif sort_by == 'price_low':
            query = query.join(TicketType).order_by(TicketType.price)
        elif sort_by == 'price_high':
            query = query.join(TicketType).order_by(TicketType.price.desc())
        
        # Group events by category if no specific category is selected
        if not category:
            events_by_category = {}
            for cat in EVENT_CATEGORIES:
                cat_events = Event.query.filter(
                    Event.date >= datetime.now(),
                    Event.status == 'approved',
                    Event.category == cat
                ).order_by(Event.date).all()
                if cat_events:
                    events_by_category[cat] = cat_events
            
            return render_template('user/events.html',
                                events_by_category=events_by_category,
                                categories=EVENT_CATEGORIES,
                                category_icons=CATEGORY_ICONS,
                                current_category=category,
                                search=search,
                                date_filter=date_filter,
                                price_filter=price_filter,
                                sort_by=sort_by)
        else:
            # If category is selected, just get those events
            events = query.all()
            return render_template('user/events.html',
                                events=events,
                                categories=EVENT_CATEGORIES,
                                category_icons=CATEGORY_ICONS,
                                current_category=category,
                                search=search,
                                date_filter=date_filter,
                                price_filter=price_filter,
                                sort_by=sort_by)
                             
    except Exception as e:
        print(f"Error loading events: {str(e)}")
        flash('Error loading events. Please try again.', 'danger')
        return render_template('user/events.html', 
                             events=[],
                             events_by_category={},
                             categories=EVENT_CATEGORIES,
                             category_icons=CATEGORY_ICONS)

@main.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status != 'approved':
        flash('This event is not currently available.', 'warning')
        return redirect(url_for('main.events'))
    return render_template('user/event_detail.html', 
                         event=event,
                         now=datetime.now())

@main.route('/terms')
def terms():
    return render_template('terms.html', 
                         current_year=datetime.now().year,
                         categories=EVENT_CATEGORIES,
                         category_icons=CATEGORY_ICONS)

@main.route('/privacy')
def privacy():
    return render_template('privacy.html', 
                         current_year=datetime.now().year,
                         categories=EVENT_CATEGORIES,
                         category_icons=CATEGORY_ICONS)

@main.route('/team')
def team():
    return render_template('team.html', 
                         current_year=datetime.now().year,
                         categories=EVENT_CATEGORIES,
                         category_icons=CATEGORY_ICONS)

# Error handlers
@main.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@main.app_errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500 