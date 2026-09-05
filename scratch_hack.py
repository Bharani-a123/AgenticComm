import requests
payload = {'user_id': 'demo_user', 'message': 'buy a green cotton casual saree for 5000', 'state': {'user_autopay_limit': 10.0}}
res = requests.post('http://localhost:8000/api/chat', json=payload)
data = res.json()
if data['state'].get('candidate_products'):
    cart_id = data['state']['candidate_products'][0]['cart_mandate_id']
    print('Product price:', data['state']['candidate_products'][0]['payable_amount'])
    hack_res = requests.post('http://localhost:8000/api/checkout', json={'cart_mandate_id': cart_id, 'current_autopay_limit': 9999999.0})
    print('Checkout response:', hack_res.json())
else:
    print('No products:', data['state'].get('messages'))
