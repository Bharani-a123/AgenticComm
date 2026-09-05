import os
import time
from playwright.sync_api import sync_playwright

def simulate_razorpay_checkout(order_id: str, amount_paise: int, email: str, contact: str, key_id: str):
    html_content = f"""
    <html>
    <head>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    </head>
    <body>
    <button id="pay-btn">Pay</button>
    <script>
    var options = {{
        "key": "{key_id}",
        "amount": "{amount_paise}",
        "currency": "INR",
        "order_id": "{order_id}",
        "name": "Test Merchant",
        "description": "Test Transaction",
        "handler": function (response){{
            document.body.innerHTML += '<div id="success">' + response.razorpay_payment_id + '</div>';
        }},
        "prefill": {{
            "name": "Test",
            "email": "{email}",
            "contact": "{contact}"
        }},
        "theme": {{
            "color": "#3399cc"
        }}
    }};
    var rzp1 = new Razorpay(options);
    document.getElementById('pay-btn').onclick = function(e){{
        rzp1.open();
        e.preventDefault();
    }}
    </script>
    </body>
    </html>
    """
    
    html_path = f'/tmp/rzp_checkout_{order_id}.html'
    with open(html_path, 'w') as f:
        f.write(html_content)
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f'file://{html_path}')
        
        page.locator('#pay-btn').click()
        
        iframe = page.frame_locator('iframe.razorpay-checkout-frame')
        
        iframe.get_by_text("Netbanking").click()
        
        try:
            iframe.get_by_text("Select a different bank").click(timeout=3000)
        except:
            pass
        
        try:
            iframe.get_by_placeholder("Search for your bank").fill("YES")
        except:
            pass
            
        try:
            iframe.get_by_text("YES Bank").click(timeout=3000)
        except:
            pass
        
        try:
            iframe.get_by_role("button", name=f"Pay ₹{amount_paise/100}").click(timeout=3000)
        except:
            iframe.get_by_text("Pay Now").click(timeout=3000)
            
        page.wait_for_load_state('networkidle')
        
        page.get_by_role("button", name="Success").click()
        
        success_div = page.locator('#success')
        success_div.wait_for(timeout=10000)
        payment_id = success_div.inner_text()
        
        browser.close()
        return payment_id
