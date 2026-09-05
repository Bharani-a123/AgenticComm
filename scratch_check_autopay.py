import requests

# 1. Chat to create an intent
payload = {
    'user_id': 'demo_user',
    'message': 'buy a green cotton casual saree for 5000',
    'state': {
        'user_autopay_limit': 2000.0,
        'user_mandate_limit': 100000.0,
        'user_payment_method': 'card_4242'
    }
}
res = requests.post('http://localhost:8000/api/chat', json=payload)
data = res.json()

# Get the cart_mandate_id of the first product
cart_id = data['state']['candidate_products'][0]['cart_mandate_id']
print('Product price:', data['state']['candidate_products'][0]['payable_amount'])

# 2. Checkout
hack_payload = {
    'cart_mandate_id': cart_id,
    'user_id': 'demo_user',
}
hack_res = requests.post('http://localhost:8000/api/checkout', json=hack_payload)
print('Checkout response:', hack_res.json())
