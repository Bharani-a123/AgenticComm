from app.db.postgres import SessionLocal
from app.db.models import PaymentMandate
db = SessionLocal()
mandate = db.query(PaymentMandate).filter(PaymentMandate.status == 'captured').order_by(PaymentMandate.created_at.desc()).first()
if mandate:
    print('Found mandate:', mandate.mandate_id)
    print('Razorpay Payment ID:', mandate.razorpay_payment_id)
    print('Amount:', mandate.amount)
    from app.services.recovery_service import handle_cancellation
    try:
        res = handle_cancellation(db, mandate.mandate_id, 'test')
        print(res)
    except Exception as e:
        print('ERROR:', e)
else:
    print('No captured mandates found')

