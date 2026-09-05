import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Sparkles, ShoppingBag, ShieldCheck } from 'lucide-react';

function Ledger() {
    const [logs, setLogs] = useState<any[]>([]);
    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const res = await axios.get('/api/audit');
                setLogs(res.data.logs);
            } catch (e) {}
        };
        fetchLogs();
        const interval = setInterval(fetchLogs, 2000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex flex-col gap-3 mt-4">
            {logs.map(log => (
                <div key={log.log_id} className="p-3 bg-gray-800 rounded-xl border border-gray-700 text-xs">
                    <div className="text-gray-400 mb-1 flex items-center gap-1">
                       <ShieldCheck size={12} /> {new Date(log.created_at).toLocaleString()}
                    </div>
                    <div className="text-blue-400 font-semibold">{log.agent_name} {'->'} {log.event_type}</div>
                    <div className="text-gray-500 font-mono mt-1 text-[10px] truncate" title={log.curr_hash}>Hash: {log.curr_hash}</div>
                    <div className="text-gray-300 mt-2 leading-relaxed">{log.reasoning}</div>
                </div>
            ))}
        </div>
    );
}

export default function App() {
  const [messages, setMessages] = useState<any[]>([]);
  const [inputText, setInputText] = useState("");
  const [state, setState] = useState<any>({ user_id: "demo_user" });
  const [loading, setLoading] = useState(false);
  
  // Payment Settings State
  const [showSettings, setShowSettings] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("card_4242");
  const [autopayLimit, setAutopayLimit] = useState<number>(2000);
  const [mandateLimit, setMandateLimit] = useState<number>(10000);

  // New State for Agentic Flow
  const [purchasedItems, setPurchasedItems] = useState<Record<string, any>>({});
  const [pendingApproval, setPendingApproval] = useState<any>(null);
  const [approvalTimer, setApprovalTimer] = useState(120);
  
  // New State for Orders Page
  const [showOrders, setShowOrders] = useState(false);
  const [orderHistory, setOrderHistory] = useState<any[]>([]);
  const [auditModal, setAuditModal] = useState<string | null>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  // Wallet State
  const [showWallet, setShowWallet] = useState(false);
  const [walletData, setWalletData] = useState<any>(null);

  // Saved Payment Methods State
  const [savedMethods, setSavedMethods] = useState<any[]>([]);
  const [savingMethod, setSavingMethod] = useState(false);

  const fetchSavedMethods = async () => {
    try {
      const res = await axios.get('/api/payment-methods?user_id=default_user');
      setSavedMethods(res.data);
    } catch (e) { console.error("Failed to fetch methods", e); }
  };

  useEffect(() => { fetchSavedMethods(); }, []);

  const loadRazorpay = () => {
    return new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = 'https://checkout.razorpay.com/v1/checkout.js';
        script.onload = () => resolve(true);
        script.onerror = () => resolve(false);
        document.body.appendChild(script);
    });
  };

  const registerToken = async () => {
    setSavingMethod(true);
    const loaded = await loadRazorpay();
    if (!loaded) {
      alert('Razorpay SDK failed to load');
      setSavingMethod(false);
      return;
    }
    
    try {
        const regRes = await axios.post('/api/payment-methods/register', { user_id: 'default_user' });
        
        const options = {
            key: "rzp_test_TT47Q6uObggWfr", 
            amount: regRes.data.amount,
            currency: regRes.data.currency,
            name: "E2E Agent Token Auth",
            description: "One-time Token Registration",
            order_id: regRes.data.order_id,
            customer_id: regRes.data.customer_id,
            handler: function (response: any) {
                alert("Token Registered Successfully! Autopay is now active.");
                fetchSavedMethods();
            }
        };
        const rzp1 = new (window as any).Razorpay(options);
        rzp1.open();
    } catch(e: any) {
        alert(e.response?.data?.detail || e.message);
    }
    setSavingMethod(false);
  };

  useEffect(() => {
    let timer: any;
    if (pendingApproval && approvalTimer > 0) {
      timer = setInterval(() => setApprovalTimer(prev => prev - 1), 1000);
    } else if (pendingApproval && approvalTimer <= 0) {
      setPendingApproval(null);
      alert("Approval window expired. Transaction canceled autonomously.");
    }
    return () => clearInterval(timer);
  }, [pendingApproval, approvalTimer]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const sendMessage = async () => {
    if (!inputText.trim()) return;
    const input = inputText;
    setMessages(prev => [...prev, { role: "user", content: input }]);
    setInputText("");
    setLoading(true);
    
    try {
      // Pass the payment limits into the state so the backend can use them
      const nextState = {
         ...state, 
         user_autopay_limit: autopayLimit,
         user_mandate_limit: mandateLimit,
         user_payment_method: paymentMethod
      };
      const res = await axios.post('/api/chat', { user_id: "demo_user", message: input, state: nextState });
      setState(res.data.state);
      setMessages(res.data.messages);
    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, { role: "assistant", content: "Error communicating with the network." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-white text-gray-800 font-sans">
       {/* Sidebar - Audit Ledger */}
       <div className="w-80 bg-gray-900 text-gray-100 flex flex-col shadow-xl z-20 hidden md:flex">
           <div className="p-5 border-b border-gray-800 flex items-center justify-between">
               <div className="flex items-center gap-2">
                   <Sparkles className="text-blue-400" />
                   <h2 className="text-lg font-semibold tracking-wide">Commerce Engine</h2>
               </div>
               <button 
                  onClick={() => setShowSettings(true)}
                  className="text-gray-400 hover:text-white transition"
                  title="Payment Settings"
               >
                  ⚙️
               </button>
           </div>
           <div className="p-4 flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
               <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Live Security Ledger</h3>
               <Ledger />
           </div>
       </div>

       {/* Payment Settings Modal */}
       {showSettings && (
           <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
               <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 text-gray-800 max-h-[90vh] overflow-y-auto">
                   <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
                      ⚙️ Payment Profile Setup
                   </h2>
                   <p className="text-sm text-gray-500 mb-6">
                      Save your card or UPI to enable autonomous AutoPay. The agent uses these saved methods to pay instantly.
                   </p>
                   
                   {/* Saved Methods List */}
                   <div className="mb-6">
                       <h3 className="text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">Saved Payment Methods</h3>
                       {savedMethods.length === 0 ? (
                           <p className="text-sm text-gray-400 italic">No methods saved yet. Add one below.</p>
                       ) : (
                           <div className="space-y-2">
                               {savedMethods.map((m: any) => (
                                   <div key={m.id} className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg p-3">
                                       <div className="flex items-center gap-3">
                                           <span className="text-xl">{m.method_type === 'card' ? '💳' : '📱'}</span>
                                           <div>
                                               <p className="font-semibold text-sm text-gray-800">
                                                   {m.method_type === 'card' ? `Card ending ${m.last_four || '****'}` : `UPI (${m.last_four || 'saved'})`}
                                               </p>
                                               <p className="text-[10px] text-gray-400 font-mono">{m.razorpay_token_id}</p>
                                           </div>
                                       </div>
                                       <button 
                                         className="text-xs text-red-500 hover:text-red-700 font-semibold"
                                         onClick={async () => {
                                             await axios.delete(`/api/payment-methods/${m.id}`);
                                             fetchSavedMethods();
                                         }}
                                       >Remove</button>
                                   </div>
                               ))}
                           </div>
                       )}
                   </div>

                   {/* Add New Method */}
                   <div className="space-y-3 mb-6">
                       <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider">Setup One-Time AutoPay Token</h3>
                       <button 
                         className="w-full bg-blue-600 text-white py-3 rounded-xl font-medium hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50"
                         disabled={savingMethod}
                         onClick={registerToken}
                       >
                         {savingMethod ? 'Loading Razorpay...' : '💳 Register Card/UPI securely via Razorpay'}
                       </button>
                       <p className="text-[10px] text-gray-400 text-center">Completing this one-time AFA setup enables the Agent to perform zero-touch S2S AutoPay charges later.</p>
                   </div>

                   {/* Limits Config */}
                   <div className="space-y-4 border-t border-gray-200 pt-4">
                       <div>
                           <label className="block text-sm font-semibold mb-1">Auto-Pay Limit (₹)</label>
                           <p className="text-xs text-gray-500 mb-2">Agent buys instantly if price is under this limit.</p>
                           <input 
                               type="number" 
                               className="w-full border border-gray-300 rounded-lg p-2.5 bg-gray-50 text-gray-900"
                               value={autopayLimit}
                               onChange={e => setAutopayLimit(Number(e.target.value))}
                           />
                       </div>

                       <div>
                           <label className="block text-sm font-semibold mb-1">Hard Mandate Limit (₹)</label>
                           <p className="text-xs text-gray-500 mb-2">Agent rejects ANY purchase over this limit.</p>
                           <input 
                               type="number" 
                               className="w-full border border-gray-300 rounded-lg p-2.5 bg-gray-50 text-gray-900"
                               value={mandateLimit}
                               onChange={e => setMandateLimit(Number(e.target.value))}
                           />
                       </div>
                   </div>

                   <div className="mt-8 flex justify-end">
                       <button 
                           onClick={() => setShowSettings(false)}
                           className="bg-blue-600 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-blue-700 transition"
                       >
                           Done
                       </button>
                   </div>
               </div>
           </div>
       )}

       {/* Main Chat Area */}
       <div className="flex-1 flex flex-col relative bg-[#f0f4f9]">
          {/* Header */}
          <header className="p-4 flex justify-between items-center bg-[#f0f4f9] z-10 sticky top-0">
             <div className="text-xl font-medium text-gray-600 flex items-center gap-2">
                <span className="bg-gradient-to-r from-blue-500 to-purple-500 text-transparent bg-clip-text font-bold">E2E Agent</span>
             </div>
             <div className="flex gap-4 items-center">
                 <button 
                     className="bg-purple-50 px-4 py-2 rounded-lg font-medium text-purple-700 border border-purple-200 hover:bg-purple-100 transition flex items-center gap-2"
                     onClick={async () => {
                         try {
                             const res = await axios.get('/api/wallet/summary?user_id=' + (state.user_id || 'demo_user'));
                             setWalletData(res.data);
                             setShowWallet(true);
                         } catch (e: any) { alert("Failed to fetch wallet data."); }
                     }}
                 >
                     <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path></svg>
                     My Wallet
                 </button>
                 <button 
                     className="bg-white px-4 py-2 rounded-lg font-medium text-blue-600 border border-blue-200 hover:bg-blue-50 transition"
                     onClick={async () => {
                         try {
                             const res = await axios.get('/api/orders?user_id=' + (state.user_id || 'demo_user'));
                             setOrderHistory(res.data);
                             setShowOrders(true);
                         } catch (e: any) { alert("Failed to fetch orders."); }
                     }}
                 >
                     View Orders
                 </button>
                 <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold">
                    U
                 </div>
             </div>
          </header>

          {/* Chat History */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 md:px-12 pb-36">
             <div className="max-w-3xl mx-auto space-y-8 pt-6">
                 {messages.length === 0 && (
                     <div className="text-center mt-20">
                        <Sparkles className="w-16 h-16 text-blue-300 mx-auto mb-6" />
                        <h1 className="text-4xl font-medium text-gray-700 mb-2">Hello, User</h1>
                        <p className="text-xl text-gray-500">What product are you looking for today?</p>
                     </div>
                 )}

                 {messages.map((m, i) => (
                     <div key={i} className={`flex gap-4 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                         {m.role === 'assistant' && (
                             <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-sm mt-1">
                                 <Sparkles size={16} />
                             </div>
                         )}
                         <div className={`max-w-[85%] ${m.role === 'user' ? 'bg-[#e3e3e3] text-gray-800 px-5 py-3 rounded-3xl' : 'text-gray-800 pt-1 leading-relaxed'}`}>
                             {m.content}
                             
                              {/* Render Checkout-Ready Showroom */}
                              {m.role === 'assistant' && i === messages.length - 1 && state.candidate_products?.length > 0 && (
                                  <div className="mt-6 w-full">
                                     <div className="flex items-center gap-2 mb-4 text-gray-500 text-sm font-semibold uppercase tracking-wider">
                                         <ShoppingBag size={16} /> Checkout-Ready Showroom
                                     </div>
                                     <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                         {state.candidate_products.map((p: any, idx: number) => (
                                            <div key={idx} className={`border p-5 rounded-2xl bg-white shadow-sm hover:shadow-md transition duration-200 ${p.budget_relaxed ? 'border-amber-300' : 'border-gray-200'}`}>
                                               {/* Header: Category + Rank + Merchant */}
                                               <div className="flex justify-between items-start mb-2">
                                                 <div>
                                                   <h3 className="font-bold text-gray-900 text-lg leading-tight">{p.product_title || p.category || 'Product'}</h3>
                                                   <span className="text-xs text-gray-500">{p.merchant_name || 'Merchant'}</span>
                                                 </div>
                                                 <div className="flex flex-col items-end gap-1">
                                                   <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full font-bold">Rank #{p.rank}</span>
                                                   <span className="text-[10px] text-gray-400">Score: {(p.final_score * 100).toFixed(0)}%</span>
                                                 </div>
                                               </div>

                                               {/* Badges */}
                                               <div className="flex flex-wrap gap-1.5 mb-3">
                                                 {p.budget_relaxed && (
                                                   <span className="bg-amber-100 text-amber-800 text-[10px] px-2 py-0.5 rounded-full font-semibold">Above Budget</span>
                                                 )}
                                                 {p.coupon_display && (
                                                   <span className="bg-green-100 text-green-800 text-[10px] px-2 py-0.5 rounded-full font-semibold">
                                                     🏷️ {p.coupon_display.code} (-₹{p.coupon_display.discount})
                                                   </span>
                                                 )}
                                                 {p.ram_gb && <span className="bg-blue-50 text-blue-700 text-[10px] px-2 py-0.5 rounded-full">{p.ram_gb}GB RAM</span>}
                                                 {p.storage_gb && <span className="bg-blue-50 text-blue-700 text-[10px] px-2 py-0.5 rounded-full">{p.storage_gb}GB</span>}
                                                 {p.camera_priority && <span className="bg-purple-50 text-purple-700 text-[10px] px-2 py-0.5 rounded-full">📸 Camera</span>}
                                                 {p.rating && <span className="bg-gray-100 text-gray-700 text-[10px] px-2 py-0.5 rounded-full">⭐ {p.rating}</span>}
                                               </div>

                                               {/* Pricing */}
                                               <div className="mb-2">
                                                 {p.coupon_display ? (
                                                   <div className="flex items-baseline gap-2">
                                                     <span className="text-2xl font-bold text-gray-900">₹{p.effective_price?.toLocaleString()}</span>
                                                     <span className="text-sm text-gray-400 line-through">₹{p.price?.toLocaleString()}</span>
                                                     <span className="text-xs text-green-600 font-semibold">Save {p.coupon_display.savings_pct}%</span>
                                                   </div>
                                                 ) : (
                                                   <span className="text-2xl font-bold text-gray-900">₹{p.effective_price?.toLocaleString() || p.price?.toLocaleString()}</span>
                                                 )}
                                               </div>

                                               {/* Explanation */}
                                               <p className="text-sm text-gray-600 mb-4 leading-relaxed">{p.explanation}</p>

                                               <button
                                                 className="w-full bg-blue-600 text-white font-medium py-2.5 rounded-xl hover:bg-blue-700 transition flex items-center justify-center gap-2"
                                                 onClick={async () => {
                                                   try {
                                                     const res = await axios.post('/api/checkout', { 
                                                        cart_mandate_id: p.cart_mandate_id, 
                                                        user_id: state.user_id || 'demo_user',
                                                        current_autopay_limit: autopayLimit,
                                                        current_mandate_limit: mandateLimit,
                                                     });
                                                     
                                                     if (res.data.status === 'auto_paid') {
                                                       setPurchasedItems(prev => ({ ...prev, [p.cart_mandate_id]: { ...res.data } }));
                                                     } else if (res.data.status === 'needs_confirmation') {
                                                       setPendingApproval({ product: p, reason: res.data.reason });
                                                       setApprovalTimer(120);
                                                     } else {
                                                         setPurchasedItems(prev => ({ 
                                                             ...prev, 
                                                             [p.cart_mandate_id]: { 
                                                                 status: res.data.status,
                                                                 error: res.data.reason, 
                                                                 pending_manual: res.data.status !== 'rejected', 
                                                                 payable_amount: p.payable_amount, 
                                                                 product_title: p.product_title 
                                                             } 
                                                         }));
                                                     }
                                                   } catch (e: any) { 
                                                     alert(`Error: ${e.response?.data?.detail || e.message}`); 
                                                   }
                                                 }}
                                               >
                                                 🛒 Select — ₹{p.payable_amount?.toLocaleString()}
                                               </button>
                                             </div>
                                         ))}
                                     </div>
                                     
                                     {/* Separate Checkout Card (Below Showroom) */}
                                     {state.candidate_products.map((p: any) => {
                                         const purchase = purchasedItems[p.cart_mandate_id];
                                         if (!purchase) return null;
                                         
                                         return (
                                             <div key={p.cart_mandate_id} className="mt-8 bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
                                                 <div className="bg-gray-50 px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                                                     <h3 className="font-semibold text-gray-800">Checkout: {p.product_title}</h3>
                                                     <span className="text-sm font-medium text-gray-500">{p.cart_mandate_id}</span>
                                                 </div>
                                                 <div className="p-6">
                                                     {purchase.status === 'rejected' ? (
                                                         <div className="text-center">
                                                            <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                                                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M6 18L18 6M6 6l12 12"></path></svg>
                                                            </div>
                                                            <h3 className="text-2xl font-bold text-gray-900 mb-1">Purchase Rejected</h3>
                                                            <p className="text-sm text-gray-600 mb-4 bg-red-50 p-3 rounded-lg border border-red-100 inline-block">{purchase.error}</p>
                                                         </div>
                                                     ) : purchase.status === 'error' || purchase.pending_manual ? (
                                                         <div>
                                                             <div className="bg-orange-50 border border-orange-200 text-orange-800 p-4 rounded-xl mb-4 text-sm">
                                                                 <strong className="block mb-1">Autonomous Capture Failed</strong>
                                                                 {purchase.error || "The agent attempted S2S recurring token capture, but it failed."}
                                                             </div>
                                                             <div className="flex items-center justify-between">
                                                                 <div>
                                                                     <p className="text-gray-500 text-sm">Amount Due</p>
                                                                     <p className="text-2xl font-bold text-gray-900">₹{p.payable_amount?.toLocaleString()}</p>
                                                                 </div>
                                                                 <button 
                                                                    className="bg-gray-900 text-white px-6 py-3 rounded-xl font-bold hover:bg-gray-800 transition"
                                                                    onClick={() => {
                                                                        // Open real Razorpay Checkout to put it in the dashboard
                                                                        const options: any = {
                                                                            key: "rzp_test_TT47Q6uObggWfr", // Hardcoded for demo
                                                                            amount: p.payable_amount * 100,
                                                                            currency: "INR",
                                                                            name: "E2E Agent",
                                                                            description: p.product_title,
                                                                            handler: function (response: any) {
                                                                                setPurchasedItems(prev => ({
                                                                                    ...prev,
                                                                                    [p.cart_mandate_id]: { 
                                                                                        status: 'captured', 
                                                                                        razorpay_order_id: response.razorpay_payment_id,
                                                                                        refunded: false
                                                                                    }
                                                                                }));
                                                                            },
                                                                            prefill: { email: "test@test.com", contact: "9999999999" },
                                                                            theme: { color: "#2563eb" }
                                                                        };
                                                                        const rzp = new (window as any).Razorpay(options);
                                                                        rzp.open();
                                                                    }}
                                                                 >
                                                                    Pay Manually (Real Razorpay UI)
                                                                 </button>
                                                             </div>
                                                         </div>
                                                     ) : purchase.status === 'auto_paid' || purchase.status === 'captured' ? (
                                                         <div className="text-center">
                                                            <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                                                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path></svg>
                                                            </div>
                                                            <h3 className="text-2xl font-bold text-gray-900 mb-1">Payment Successful</h3>
                                                            <p className="text-sm text-gray-500 mb-4">Order ID: <span className="font-mono text-gray-800">{purchase.razorpay_order_id}</span></p>
                                                            
                                                            <div className="flex justify-center gap-3">
                                                                <button 
                                                                    className="bg-red-50 text-red-700 px-4 py-2 rounded-lg font-semibold hover:bg-red-100 disabled:opacity-50"
                                                                    disabled={purchase.refunded}
                                                                    onClick={async () => {
                                                                        try {
                                                                            await axios.post('/api/checkout/cancel', { cart_mandate_id: p.cart_mandate_id, reason: "User requested refund" });
                                                                            setPurchasedItems(prev => ({ ...prev, [p.cart_mandate_id]: { ...prev[p.cart_mandate_id], refunded: true } }));
                                                                        } catch (e: any) { alert("Refund failed: " + (e.response?.data?.detail || e.message)); }
                                                                    }}
                                                                >
                                                                    {purchase.refunded ? "Refunded ✅" : "Cancel & Refund"}
                                                                </button>
                                                                <button 
                                                                    className="bg-blue-50 text-blue-700 px-4 py-2 rounded-lg font-semibold hover:bg-blue-100"
                                                                    onClick={async () => {
                                                                        try {
                                                                            const res = await axios.get('/api/audit?reference_id=' + p.cart_mandate_id);
                                                                            setAuditLogs(res.data.logs);
                                                                            setAuditModal(p.cart_mandate_id);
                                                                        } catch (e) { alert("Failed to fetch audit trail"); }
                                                                    }}
                                                                >
                                                                    View Agent Audit Trail
                                                                </button>
                                                            </div>
                                                         </div>
                                                     ) : null}
                                                 </div>
                                             </div>
                                         );
                                     })}
                                  </div>
                              )}

                             {/* Render Missing Fields Form */}
                             {m.role === 'assistant' && i === messages.length - 1 && state.missing_fields?.length > 0 && (
                                 <div className="mt-4 p-4 border border-blue-200 bg-blue-50 rounded-xl">
                                     <h4 className="font-semibold text-blue-800 mb-3 text-sm uppercase tracking-wider">Please provide missing details</h4>
                                     <form onSubmit={(e) => {
                                         e.preventDefault();
                                         const fd = new FormData(e.currentTarget);
                                         let submission = "";
                                         fd.forEach((val, key) => {
                                             if (val) submission += `${key}: ${val}, `;
                                         });
                                         if (submission) {
                                             setInputText(submission.slice(0, -2));
                                             // We wait a tick to allow state to update, or directly send
                                             setTimeout(() => {
                                                const submitBtn = document.getElementById("main-send-btn");
                                                if (submitBtn) submitBtn.click();
                                             }, 50);
                                         }
                                     }}>
                                         {state.missing_fields.map((field: string) => (
                                             <div key={field} className="mb-3">
                                                 <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">{field.replace('_', ' ')}</label>
                                                 {Array.isArray(state.missing_field_options?.[field]) ? (
                                                     <select name={field} className="w-full border-gray-300 rounded-md p-2 shadow-sm text-sm" required>
                                                         <option value="">Select {field}</option>
                                                         {state.missing_field_options[field].map((opt: string) => (
                                                             <option key={opt} value={opt}>{opt}</option>
                                                         ))}
                                                     </select>
                                                 ) : (
                                                     <input type="text" name={field} placeholder={`Enter ${field}`} className="w-full border-gray-300 rounded-md p-2 shadow-sm text-sm" required />
                                                 )}
                                             </div>
                                         ))}
                                         <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium mt-2 hover:bg-blue-700">Submit Details</button>
                                     </form>
                                 </div>
                             )}
                         </div>
                     </div>
                 ))}
                 {loading && (
                     <div className="flex gap-4 justify-start">
                         <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-sm animate-pulse">
                             <Sparkles size={16} />
                         </div>
                         <div className="pt-2 text-gray-400 italic animate-pulse">
                             Thinking...
                         </div>
                     </div>
                 )}
                 <div ref={messagesEndRef} />
             </div>
          </div>
          
          {/* Floating Input Box */}
          <div className="absolute bottom-0 w-full bg-gradient-to-t from-[#f0f4f9] via-[#f0f4f9] to-transparent pt-10 pb-6 px-4 sm:px-6 md:px-12 pointer-events-none">
             <div className="max-w-3xl mx-auto relative pointer-events-auto">
                 <input 
                    type="text" 
                    className="w-full bg-white border border-gray-200 shadow-lg text-gray-800 placeholder-gray-500 rounded-full pl-6 pr-14 py-4 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="Ask E2E Agent..." 
                    value={inputText} 
                    onChange={e => setInputText(e.target.value)} 
                    onKeyDown={e => e.key === 'Enter' && sendMessage()} 
                    disabled={loading}
                 />
                 <button 
                    id="main-send-btn"
                    onClick={sendMessage} 
                    disabled={loading || !inputText.trim()} 
                    className="absolute right-2 top-2 bottom-2 bg-blue-600 text-white p-3 rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:bg-gray-300 transition-colors flex items-center justify-center"
                 >
                    <Send size={18} />
                 </button>
             </div>
             <div className="text-center mt-3 text-xs text-gray-500 font-medium">
                 Agents can make mistakes. The safety ledger on the left enforces mathematical limits.
             </div>
          </div>
       </div>
       
       {pendingApproval && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-2xl max-w-sm w-full">
            <h3 className="text-lg font-bold mb-2">Payment Requires Approval</h3>
            <p className="text-sm text-gray-600 mb-4">{pendingApproval.reason}</p>
            <div className="text-3xl font-mono font-bold text-center text-blue-600 mb-6">
              {Math.floor(approvalTimer / 60)}:{(approvalTimer % 60).toString().padStart(2, '0')}
            </div>
            <div className="flex gap-3">
              <button 
                className="flex-1 bg-gray-200 text-gray-800 py-2 rounded-lg font-medium hover:bg-gray-300"
                onClick={() => setPendingApproval(null)}
              >
                Decline
              </button>
              <button 
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700"
                onClick={async () => {
                   try {
                       const confirmRes = await axios.post('/api/checkout/confirm', { 
                          cart_mandate_id: pendingApproval.product.cart_mandate_id, 
                          confirmed: true, 
                          user_id: state.user_id || 'demo_user',
                          current_autopay_limit: autopayLimit,
                          current_mandate_limit: mandateLimit,
                          user_payment_method: paymentMethod
                       });
                       if (confirmRes.data.status === 'confirmed_paid') {
                          setPurchasedItems(prev => ({ ...prev, [pendingApproval.product.cart_mandate_id]: { razorpay_order_id: confirmRes.data.razorpay_order_id } }));
                          setPendingApproval(null);
                       } else {
                          alert(`Status: ${confirmRes.data.status} — ${confirmRes.data.reason || ''}`);
                       }
                   } catch (e: any) { alert(`Error: ${e.response?.data?.detail || e.message}`); }
                }}
              >
                Approve & Pay
              </button>
            </div>
          </div>
        </div>
       )}

         {showWallet && walletData && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white p-8 rounded-2xl shadow-2xl max-w-3xl w-full flex flex-col">
              <div className="flex justify-between items-center mb-8">
                <h3 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                    <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path></svg>
                    Mandate Wallet
                </h3>
                <button onClick={() => setShowWallet(false)} className="text-gray-500 hover:text-gray-800">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
                  <div className="bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl p-6 text-white shadow-lg">
                      <div className="text-purple-100 text-sm font-semibold mb-1 uppercase tracking-wider">Available Budget</div>
                      <div className="text-4xl font-bold font-mono">₹{walletData.available_budget.toLocaleString()}</div>
                      <div className="mt-4 text-xs text-purple-200">Total Allocation - Net Spent</div>
                  </div>
                  
                  <div className="bg-gray-50 border border-gray-200 rounded-2xl p-6 flex flex-col justify-center">
                      <div className="flex justify-between items-start">
                          <div className="text-gray-500 text-sm font-semibold mb-1 uppercase tracking-wider">Total Lifetime Allocation</div>
                          <button 
                              className="text-blue-600 text-sm font-bold hover:underline"
                              onClick={async () => {
                                  const amt = prompt("Set your global wallet allocation (e.g. 50000):", walletData.total_budget_allocated);
                                  if (amt && !isNaN(Number(amt))) {
                                      await axios.post('/api/wallet/allocate', { user_id: state.user_id || 'demo_user', amount: Number(amt) });
                                      const res = await axios.get('/api/wallet/summary?user_id=' + (state.user_id || 'demo_user'));
                                      setWalletData(res.data);
                                  }
                              }}
                          >
                              Edit
                          </button>
                      </div>
                      <div className="text-3xl font-bold text-gray-900 font-mono">₹{walletData.total_budget_allocated.toLocaleString()}</div>
                  </div>
              </div>

              <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
                  <div className="grid grid-cols-3 divide-x divide-gray-200 text-center">
                      <div className="p-4">
                          <div className="text-gray-500 text-xs font-bold uppercase tracking-wider mb-1">Lifetime Spent</div>
                          <div className="text-xl font-bold text-red-600">₹{walletData.total_amount_captured.toLocaleString()}</div>
                      </div>
                      <div className="p-4 bg-yellow-50">
                          <div className="text-yellow-700 text-xs font-bold uppercase tracking-wider mb-1">Pending Refunds</div>
                          <div className="text-xl font-bold text-yellow-700">₹{walletData.total_amount_pending_refund?.toLocaleString() || 0}</div>
                      </div>
                      <div className="p-4 bg-green-50">
                          <div className="text-green-700 text-xs font-bold uppercase tracking-wider mb-1">Lifetime Refunded</div>
                          <div className="text-xl font-bold text-green-700">₹{walletData.total_amount_refunded.toLocaleString()}</div>
                      </div>
                  </div>
              </div>
            </div>
          </div>
         )}

         {showOrders && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white p-6 rounded-xl shadow-2xl max-w-4xl w-full max-h-[80vh] flex flex-col">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900">Your Orders</h3>
                <button onClick={() => setShowOrders(false)} className="text-gray-500 hover:text-gray-800">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
              </div>
              <div className="flex-1 overflow-y-auto space-y-4">
                 {orderHistory.length === 0 ? <p className="text-center text-gray-500 py-10">No orders found.</p> : orderHistory.map((order: any) => (
                    <div key={order.payment_mandate_id} className="border border-gray-200 rounded-xl p-5 flex flex-col justify-between items-start bg-gray-50 hover:bg-gray-100 transition gap-4">
                       <div className="flex justify-between w-full items-start">
                           <div>
                              <h4 className="font-bold text-lg text-gray-900">{order.product_title}</h4>
                              <div className="text-sm text-gray-500 mt-1">Order ID: <span className="font-mono">{order.razorpay_order_id || 'N/A'}</span></div>
                              <div className="text-sm text-gray-500">Date: {new Date(order.created_at).toLocaleString()}</div>
                           </div>
                           <div className="flex flex-col items-end">
                              <span className="text-xl font-bold">₹{order.payable_amount.toLocaleString()}</span>
                              <span className={`text-xs font-bold px-2 py-1 rounded-full mt-2 uppercase ${order.status === 'captured' ? 'bg-green-100 text-green-700' : order.status === 'refunded' ? 'bg-purple-100 text-purple-700' : (order.status === 'pending' || order.status === 'pending_refund') ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                                 {order.status.replace('_', ' ')}
                              </span>
                           </div>
                       </div>
                       
                       <div className="flex flex-wrap gap-3 w-full border-t border-gray-200 pt-4">
                            {(order.status === 'captured' || order.status === 'refunded' || order.status === 'pending_refund') && (
                                <button 
                                    className="bg-white border border-red-200 text-red-700 px-4 py-2 rounded-lg font-semibold hover:bg-red-50 disabled:opacity-50 text-sm"
                                    disabled={order.status === 'refunded' || order.status === 'pending_refund'}
                                    onClick={async () => {
                                        try {
                                            await axios.post('/api/checkout/cancel', { cart_mandate_id: order.cart_mandate_id, reason: "User requested refund from orders page" });
                                            // Refresh orders
                                            const res = await axios.get('/api/orders?user_id=' + (state.user_id || 'demo_user'));
                                            setOrderHistory(res.data);
                                            const res2 = await axios.get('/api/wallet/summary?user_id=' + (state.user_id || 'demo_user'));
                                            setWalletData(res2.data);
                                        } catch (e: any) { alert("Refund failed: " + (e.response?.data?.detail || e.message)); }
                                    }}
                                >
                                    {order.status === 'refunded' ? "Refunded 💸" : order.status === 'pending_refund' ? "Refund Processing ⏳" : "Cancel & Refund"}
                                </button>
                            )}
                            <button 
                                className="bg-white border border-blue-200 text-blue-700 px-4 py-2 rounded-lg font-semibold hover:bg-blue-50 text-sm ml-auto"
                                onClick={async () => {
                                    try {
                                        const res = await axios.get('/api/audit?reference_id=' + order.cart_mandate_id);
                                        setAuditLogs(res.data.logs);
                                        setAuditModal(order.cart_mandate_id);
                                    } catch (e) { alert("Failed to fetch audit trail"); }
                                }}
                            >
                                View Agent Audit Trail
                            </button>
                       </div>
                    </div>
                 ))}
              </div>
            </div>
          </div>
         )}

       {auditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-2xl max-w-lg w-full max-h-[80vh] flex flex-col">
            <h3 className="text-lg font-bold mb-4">Audit Trail for {auditModal}</h3>
            <div className="flex-1 overflow-y-auto space-y-3 mb-4">
               {auditLogs.length === 0 ? <p className="text-sm text-gray-500">No logs found.</p> : auditLogs.map(log => (
                 <div key={log.log_id} className="text-xs bg-gray-50 p-3 rounded border border-gray-200">
                   <div className="font-semibold text-gray-700 mb-1">{log.agent_name} - <span className="text-blue-600">{log.event_type}</span></div>
                   <div className="text-gray-500 mb-1">{new Date(log.created_at).toLocaleString()}</div>
                   <div className="text-gray-800 italic">{log.reasoning}</div>
                 </div>
               ))}
            </div>
            <button 
              className="w-full bg-gray-200 text-gray-800 py-2 rounded-lg font-medium hover:bg-gray-300"
              onClick={() => setAuditModal(null)}
            >
              Close
            </button>
          </div>
        </div>
       )}

    </div>
  );
}
