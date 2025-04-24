import requests
from flask import current_app
import json
from datetime import datetime
import os

class PaystackPayment:
    def __init__(self):
        self.secret_key = current_app.config['PAYSTACK_SECRET_KEY']
        self.base_url = 'https://api.paystack.co'
        
    def initialize_payment(self, email, amount, reference, callback_url):
        """Initialize a payment transaction"""
        try:
            headers = {
                'Authorization': f"Bearer {self.secret_key}",
                'Content-Type': 'application/json'
            }
            
            data = {
                'email': email,
                'amount': int(amount * 100),  # Convert to pesewas
                'reference': reference,
                'callback_url': callback_url,
                'currency': 'GHS'  # Explicitly set currency to Ghana Cedis
            }
            
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()['data']
            return None
            
        except Exception as e:
            print(f"Paystack initialization error: {str(e)}")
            return None

    def verify_payment(self, reference):
        """Verify a payment transaction"""
        try:
            headers = {
                'Authorization': f"Bearer {self.secret_key}",
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()['data']
            return None
            
        except Exception as e:
            print(f"Paystack verification error: {str(e)}")
            return None