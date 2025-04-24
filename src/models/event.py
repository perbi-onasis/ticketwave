from datetime import datetime
from src.models import db

# Event Categories
EVENT_CATEGORIES = [
    'nightlife_parties',
    'movies_cinema',
    'arts_theatre',
    'food_drinks',
    'networking',
    'travel_outdoor',
    'professional',
    'health_wellness',
    'family_education',
    'charity_causes',
    'science_technology',
    'religion_spirituality',
    'community_culture',
    'fashion',
    'esports',
    'sports',
    'other'
]

# Ticket Types
TICKET_TYPES = [
    'general_admission',
    'reserved_seating',
    'vip_seating',
    'group_tickets',
    'early_bird',
    'hidden_tickets',
    'free_events',
    'child_ticket',
    'student_ticket'
]

class Event(db.Model):
    __tablename__ = 'event'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(200))
    promoter = db.Column(db.String(100), db.ForeignKey('user.username'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)  # For multi-day events
    venue = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Ghana')
    status = db.Column(db.String(20), default='approved')  # Changed from 'pending' to 'approved'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    max_capacity = db.Column(db.Integer)
    current_capacity = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    is_private = db.Column(db.Boolean, default=False)
    is_cancelled = db.Column(db.Boolean, default=False)
    cancellation_reason = db.Column(db.Text)
    location_lat = db.Column(db.Float)
    location_lng = db.Column(db.Float)
    age_restriction = db.Column(db.String(50))
    website_url = db.Column(db.String(200))
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    
    # Relationships
    ticket_types = db.relationship('TicketType', backref='event', lazy=True, cascade='all, delete-orphan')
    promotions = db.relationship('Promotion', backref='event', lazy=True, cascade='all, delete-orphan')
    tickets = db.relationship('Ticket', back_populates='event', cascade='all, delete-orphan')

    @property
    def total_tickets_sold(self):
        return sum(ticket_type.quantity - ticket_type.available 
                  for ticket_type in self.ticket_types)
    
    @property
    def total_revenue(self):
        return sum(ticket.price_paid for ticket in self.tickets 
                  if ticket.payment_status == 'completed')

    @property
    def is_sold_out(self):
        return all(tt.available == 0 for tt in self.ticket_types)

    @property
    def is_upcoming(self):
        return self.date > datetime.now()

    @property
    def is_ongoing(self):
        now = datetime.now()
        if self.end_date:
            return self.date <= now <= self.end_date
        return self.date.date() == now.date()

    @property
    def tickets_available(self):
        return sum(tt.available for tt in self.ticket_types)

    @property
    def lowest_price(self):
        prices = [tt.price for tt in self.ticket_types if tt.available > 0]
        return min(prices) if prices else None

    def get_status_display(self):
        if self.is_cancelled:
            return 'Cancelled'
        if self.date < datetime.now():
            return 'Past'
        if self.is_sold_out:
            return 'Sold Out'
        return self.status.title()

class TicketType(db.Model):
    __tablename__ = 'ticket_type'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    available = db.Column(db.Integer, nullable=False)
    max_per_order = db.Column(db.Integer, default=10)
    min_per_order = db.Column(db.Integer, default=1)
    sale_start_date = db.Column(db.DateTime)
    sale_end_date = db.Column(db.DateTime)
    is_hidden = db.Column(db.Boolean, default=False)
    requires_verification = db.Column(db.Boolean, default=False)
    benefits = db.Column(db.Text)  # List of perks/benefits
    color_code = db.Column(db.String(7))  # For UI differentiation
    position = db.Column(db.Integer, default=0)  # For display order

    tickets = db.relationship('Ticket', back_populates='ticket_type')

    @property
    def is_available(self):
        now = datetime.now()
        return (
            self.available > 0 
            and (not self.sale_start_date or self.sale_start_date <= now)
            and (not self.sale_end_date or self.sale_end_date >= now)
            and not self.is_hidden
        )

    @property
    def percentage_sold(self):
        if self.quantity == 0:
            return 0
        return ((self.quantity - self.available) / self.quantity) * 100

class Promotion(db.Model):
    __tablename__ = 'promotion'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_type = db.Column(db.String(20), default='percentage')  # percentage or fixed
    discount_amount = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    terms_conditions = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    max_uses = db.Column(db.Integer)
    current_uses = db.Column(db.Integer, default=0)
    min_ticket_count = db.Column(db.Integer, default=1)
    min_order_amount = db.Column(db.Float, default=0)
    applicable_ticket_types = db.Column(db.String(200))
    
    tickets = db.relationship('Ticket', back_populates='used_promotion')

    @property
    def is_valid(self):
        now = datetime.now()
        return (
            self.is_active 
            and self.start_date <= now <= self.end_date
            and (not self.max_uses or self.current_uses < self.max_uses)
        )

    def calculate_discount(self, original_price):
        if self.discount_type == 'percentage':
            return (original_price * self.discount_amount) / 100
        return self.discount_amount 