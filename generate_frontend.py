import os
import subprocess

def run(cmd, cwd=None):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)

if not os.path.exists("frontend"):
    run("npm create vite@latest frontend -- --template react-ts")

os.chdir("frontend")
run("npm install")
run("npm install tailwindcss postcss autoprefixer axios")
run("npx tailwindcss init -p")

with open("tailwind.config.js", "w") as f:
    f.write('''
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
''')

with open("src/index.css", "w") as f:
    f.write('''
@tailwind base;
@tailwind components;
@tailwind utilities;
body { background-color: #f9fafb; font-family: ui-sans-serif, system-ui, sans-serif; }
''')

with open("vite.config.ts", "w") as f:
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
       <div className="w-2/3 flex flex-col border-r">
          <div className="bg-white p-4 shadow-sm border-b font-bold text-xl text-gray-800 flex items-center">
             ? Agentic Commerce UI
          </div>
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
             {messages.map((m, i) => (
                 <div key={i} className={lex }>
                     <div className={max-w-[70%] p-3 rounded-2xl }>
                         {m.content}
                     </div>
                 </div>
             ))}
             {loading && (
                 <div className="flex justify-start">
                     <div className="p-3 rounded-2xl bg-gray-100 text-gray-500 italic">Agent is thinking...</div>
                 </div>
             )}
             
             {state.candidate_products?.length > 0 && !loading && (
                 <div className="mt-6">
                    <h3 className="font-bold text-gray-700 mb-2">Showroom (Pre-filtered & Ranked by Agents)</h3>
                    <div className="grid grid-cols-2 gap-4">
                        {state.candidate_products.map((p: any, i: number) => (
                           <div key={i} className="border p-4 rounded-xl bg-white shadow-sm flex flex-col justify-between hover:shadow-md transition">
                              <div>
                                  <div className="flex justify-between items-start">
                                    <h3 className="font-bold text-lg">{p.category || 'Product'}</h3>
                                    <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded font-bold">Rank #{p.rank}</span>
                                  </div>
                                  <p className="text-green-600 font-bold mt-1">?{p.price}</p>
                                  <p className="text-sm text-gray-600 mt-2">{p.explanation}</p>
                              </div>
                              <button className="mt-4 bg-black text-white px-4 py-2 rounded-lg font-medium hover:bg-gray-800 w-full">Buy with AutoPay</button>
                           </div>
                        ))}
                    </div>
                 </div>
             )}
          </div>
          <div className="p-4 bg-white border-t">
             <div className="flex gap-2">
                 <input 
                    type="text" 
                    className="flex-1 border p-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500" 
                    placeholder="Ask for a product (e.g., 'I need a red silk saree under ?3000')" 
                    value={inputText} 
                    onChange={e => setInputText(e.target.value)} 
                    onKeyDown={e => e.key === 'Enter' && sendMessage()} 
                 />
                 <button onClick={sendMessage} disabled={loading} className="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold disabled:opacity-50">Send</button>
             </div>
          </div>
       </div>
       <div className="w-1/3 bg-gray-900 text-green-400 p-6 overflow-y-auto font-mono text-sm">
           <h2 className="text-white text-lg font-bold mb-4 flex items-center gap-2">
               ?? Immutable Audit Ledger
           </h2>
           <Ledger />
       </div>
    </div>
  );
}
'''
with open("src/App.tsx", "w") as f:
    f.write(app_tsx)
