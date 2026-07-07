from app import app, db, User, WithdrawalRequest
from werkzeug.security import generate_password_hash
import uuid

with app.app_context():
    # Create 1@1.1
    user1 = User.query.filter_by(email='1@1.1').first()
    if not user1:
        user1 = User(
            username='user_reject',
            email='1@1.1',
            password_hash=generate_password_hash('123456'),
            referral_code=str(uuid.uuid4())[:8],
            goal_choice='money',
            fast_goal_tasks_completed=100
        )
        db.session.add(user1)
        db.session.commit()
    
    # Create rejected withdrawal
    if not WithdrawalRequest.query.filter_by(user_id=user1.id, status='rejected').first():
        req1 = WithdrawalRequest(
            user_id=user1.id,
            amount=80.0,
            ccp_account='123456',
            payment_method='ccp',
            status='rejected',
            rejection_reason='لم تكمل المهام بشكل صحيح'
        )
        db.session.add(req1)

    # Create 2@2.2
    user2 = User.query.filter_by(email='2@2.2').first()
    if not user2:
        user2 = User(
            username='user_accept',
            email='2@2.2',
            password_hash=generate_password_hash('123456'),
            referral_code=str(uuid.uuid4())[:8],
            goal_choice='money',
            fast_goal_tasks_completed=100
        )
        db.session.add(user2)
        db.session.commit()
    
    # Create approved withdrawal
    if not WithdrawalRequest.query.filter_by(user_id=user2.id, status='approved').first():
        req2 = WithdrawalRequest(
            user_id=user2.id,
            amount=80.0,
            ccp_account='654321',
            payment_method='ccp',
            status='approved'
        )
        db.session.add(req2)
        
    db.session.commit()
    print("Test accounts created")
