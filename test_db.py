import traceback
from app import app, db, User
from flask import request

with app.app_context():
    # Login a user
    with app.test_client() as client:
        # Create a test user
        u = User.query.filter_by(email="test@test.com").first()
        if not u:
            u = User(username="test", email="test@test.com", password_hash="123", referral_code="test")
            db.session.add(u)
            db.session.commit()
            
        with client.session_transaction() as sess:
            sess['_user_id'] = str(u.id)
            
        response = client.post('/settings', data={
            'ccp_account': 'myccp',
            'instagram_username': 'myinsta',
            'tiktok_username': 'mytik',
            'auto_withdraw_threshold': '40'
        })
        print(response.status_code)
        if response.status_code >= 500:
            print(response.data.decode('utf-8'))
