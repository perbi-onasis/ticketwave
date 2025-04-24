from datetime import datetime
from src.models import db
import qrcode
import io
import base64

class Ticket(db.Model):
    __tablename__ = 'ticket'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    ticket_type_id = db.Column(db.Integer, db.ForeignKey('ticket_type.id'), nullable=False)
    promotion_id = db.Column(db.Integer, db.ForeignKey('promotion.id'), nullable=True)
    price_paid = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(20), nullable=True)
    transaction_id = db.Column(db.String(100), nullable=True)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    guest_name = db.Column(db.String(100))
    guest_email = db.Column(db.String(120))
    guest_phone = db.Column(db.String(20))
    is_used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationships
    event = db.relationship('Event', back_populates='tickets')
    ticket_type = db.relationship('TicketType', back_populates='tickets')
    used_promotion = db.relationship('Promotion', back_populates='tickets')
    user = db.relationship('User', back_populates='tickets')
    
    def generate_qr_code(self):
        # Generate QR code data
        qr_data = f"""
        Event: {self.event.name}
        Ticket #: {self.ticket_number}
        Type: {self.ticket_type.name}
        Guest: {self.guest_name}
        Date: {self.event.date.strftime('%B %d, %Y %I:%M %p')}
        Venue: {self.event.venue}
        """
        
        # Create QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding in email/webpage
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode() 