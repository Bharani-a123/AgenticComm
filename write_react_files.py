import os

with open("frontend/tailwind.config.js", "w") as f:
    f.write('''
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
''')

with open("frontend/src/index.css", "w") as f:
    f.write('''
@tailwind base;
@tailwind components;
@tailwind utilities;
body { background-color: #f9fafb; font-family: ui-sans-serif, system-ui, sans-serif; }
''')

with open("frontend/vite.config.ts", "w") as f:
    f.write('''
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
})
''')

app_tsx = '''
import React, { useState, useEffect } from 'react';
import axios from 'axios';

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
        <div className="text-xs">
            {logs.map(log => (
                <div key={log.log_id} className="mb-4 border-b border-gray-700 pb-2">
                    <div className="text-gray-500">[{log.created_at}]</div>
                    <div className="text-blue-400 font-bold">{log.agent_name} -> {log.event_type}</div>
                    <div className="text-gray-400 truncate">Hash: {log.curr_hash}</div>
                    <div className="text-white mt-1">{log.reasoning}</div>
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
  
  const sendMessage = async () => {
    if (!inputText.trim()) return;
    const input = inputText;
    setMessages(prev => [...prev, { role: "user", content: input }]);
    setInputText("");
    setLoading(true);
    
    try {
      const res = await axios.post('/api/chat', { user_id: "demo_user", message: input, state: state });
      setState(res.data.state);
      setMessages(res.data.messages);
    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, { role: "assistant", content: "Error communicating with Agent." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
       <div className="w-2/3 flex flex-col border-r relative">
          <div className="bg-white p-4 shadow-sm border-b font-bold text-xl text-gray-800 flex items-center justify-between z-10">
             <span>? Agentic Commerce UI (Gemini Powered)</span>
          </div>
          <div className="flex-1 overflow-y-auto p-6 space-y-4 pb-24">
             {messages.map((m, i) => (
                 <div key={i} className={lex }>
                     <div className={max-w-[70%] p-4 rounded-2xl }>
                         {m.content}
                     </div>
                 </div>
             ))}
             {loading && (
                 <div className="flex justify-start">
                     <div className="p-4 rounded-2xl bg-gray-100 text-gray-500 italic animate-pulse">Agent is thinking...</div>
                 </div>
             )}
             
             {state.candidate_products?.length > 0 && !loading && (
                 <div className="mt-6 border-t pt-4">
                    <h3 className="font-bold text-gray-700 mb-4">Showroom (Pre-filtered & Ranked by Agents)</h3>
                    <div className="grid grid-cols-2 gap-4">
                        {state.candidate_products.map((p: any, i: number) => (
                           <div key={i} className="border p-5 rounded-2xl bg-white shadow-sm flex flex-col justify-between hover:shadow-md transition">
                              <div>
                                  <div className="flex justify-between items-start mb-2">
                                    <h3 className="font-bold text-lg text-gray-900">{p.category || 'Product'}</h3>
                                    <span className="bg-gradient-to-r from-yellow-200 to-yellow-400 text-yellow-900 text-xs px-2 py-1 rounded font-bold shadow-sm">Rank #{p.rank}</span>
                                  </div>
                                  <p className="text-green-600 font-extrabold text-xl mt-1">?{p.price}</p>
                                  <p className="text-sm text-gray-600 mt-3 leading-relaxed">{p.explanation}</p>
                              </div>
                              <button className="mt-5 bg-gray-900 text-white px-4 py-3 rounded-xl font-bold hover:bg-gray-800 w-full transition transform hover:scale-105 active:scale-95 shadow-md">Buy with AutoPay</button>
                           </div>
                        ))}
                    </div>
                 </div>
             )}
          </div>
          
          <div className="absolute bottom-0 w-full p-4 bg-gradient-to-t from-gray-50 to-transparent">
             <div className="flex gap-2 max-w-3xl mx-auto shadow-xl rounded-2xl bg-white p-2">
                 <input 
                    type="text" 
                    className="flex-1 border-none p-3 rounded-xl focus:outline-none focus:ring-0 text-gray-700 bg-transparent" 
                    placeholder="Ask for a product (e.g., 'I need a red silk saree under ?3000')" 
                    value={inputText} 
                    onChange={e => setInputText(e.target.value)} 
                    onKeyDown={e => e.key === 'Enter' && sendMessage()} 
                 />
                 <button onClick={sendMessage} disabled={loading} className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold disabled:opacity-50 transition">Send</button>
             </div>
          </div>
       </div>
       <div className="w-1/3 bg-gray-950 text-green-400 p-6 overflow-y-auto font-mono text-sm">
           <h2 className="text-white text-lg font-bold mb-6 flex items-center gap-2 border-b border-gray-800 pb-4">
               ?? Immutable Audit Ledger
           </h2>
           <Ledger />
       </div>
    </div>
  );
}
'''
with open("frontend/src/App.tsx", "w") as f:
    f.write(app_tsx)
