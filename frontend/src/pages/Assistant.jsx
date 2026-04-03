import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Trash2, TrendingUp } from 'lucide-react';
import { sendChat } from '../api';

const PROMPTS = [
  'What is the current price of TCS?',
  'Give me the fundamental analysis of HDFC Bank',
  'Compare IT sector stocks by ROE',
  'Is the NSE market open right now?',
  'What is the RSI and MA for Reliance?',
  'News sentiment for Infosys today',
  'Which banking stocks have the best P/E?',
  'Show me Bajaj Finance fundamentals',
];

function ThinkingDots() {
  return (
    <div className="chat-bubble loading">
      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
        <Bot size={16} color="var(--accent)"/>
        <span style={{ fontSize:12, color:'var(--text-2)', fontFamily:'var(--font-mono)' }}>Analysing</span>
        <div className="loading-dots" style={{ display:'inline-flex' }}>
          <span/><span/><span/>
        </div>
      </div>
    </div>
  );
}

export default function Assistant() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hello! I'm your Financial AI Assistant powered by Gemini 2.5 Flash.\n\nI can help you with:\n• Live stock prices & technical indicators (RSI, MA)\n• Fundamental analysis (P/E, ROE, debt ratios)\n• News sentiment for any company\n• Sector-wide comparisons\n• NSE/BSE market status\n\nWhat would you like to know?",
    }
  ]);
  const [input, setInput]     = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const textRef   = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput('');
    setMessages(m => [...m, { role: 'user', content: msg }]);
    setLoading(true);
    try {
      const { response } = await sendChat(msg);
      setMessages(m => [...m, { role: 'assistant', content: response }]);
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        (err?.code === 'ECONNABORTED'
          ? 'Request timed out while waiting for AI response. Please try again.'
          : null) ||
        err?.message ||
        'Failed to get a response. Please check backend/API key/quota.';
      setMessages(m => [...m, { role: 'assistant', content: `⚠ ${detail}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <div>
      <div className="card fade-up" style={{ padding:0, overflow:'hidden' }}>
        {/* Header */}
        <div style={{ padding:'18px 24px', borderBottom:'1px solid var(--border)', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
          <div className="flex gap-10 items-center">
            <div style={{ width:36, height:36, background:'var(--accent-dim)', borderRadius:10, display:'flex', alignItems:'center', justifyContent:'center' }}>
              <Bot size={18} color="var(--accent)"/>
            </div>
            <div>
              <div style={{ fontFamily:'var(--font-display)', fontWeight:700, fontSize:15 }}>Financial AI Assistant</div>
              <div style={{ fontSize:11, color:'var(--text-3)', fontFamily:'var(--font-mono)' }}>Gemini 2.5 Flash · LangGraph ReAct</div>
            </div>
          </div>
          {messages.length > 1 && (
            <button className="btn-icon danger" onClick={() => setMessages([messages[0]])} title="Clear chat">
              <Trash2 size={14}/>
            </button>
          )}
        </div>

        {/* Suggested prompts */}
        {messages.length <= 1 && (
          <div className="prompt-chips">
            {PROMPTS.map(p => (
              <button key={p} className="chip" onClick={() => send(p)}>{p}</button>
            ))}
          </div>
        )}

        {/* Messages */}
        <div className="chat-messages" style={{ minHeight:420 }}>
          {messages.map((m, i) => (
            <div key={i} style={{ display:'flex', gap:10, alignItems:'flex-start', flexDirection: m.role==='user' ? 'row-reverse' : 'row' }}>
              <div style={{
                width:30, height:30, borderRadius:'50%', flexShrink:0,
                background: m.role==='user' ? 'var(--accent)' : 'var(--bg-3)',
                display:'flex', alignItems:'center', justifyContent:'center',
              }}>
                {m.role==='user'
                  ? <User size={14} color="#000"/>
                  : <Bot size={14} color="var(--accent)"/>
                }
              </div>
              <div className={`chat-bubble ${m.role}`}>{m.content}</div>
            </div>
          ))}
          {loading && (
            <div style={{ display:'flex', gap:10, alignItems:'flex-start' }}>
              <div style={{ width:30, height:30, borderRadius:'50%', background:'var(--bg-3)', display:'flex', alignItems:'center', justifyContent:'center' }}>
                <Bot size={14} color="var(--accent)"/>
              </div>
              <ThinkingDots/>
            </div>
          )}
          <div ref={bottomRef}/>
        </div>

        {/* Input */}
        <div className="chat-input-row">
          <textarea
            ref={textRef}
            className="chat-input"
            rows={1}
            placeholder="Ask about stocks, fundamentals, RSI, market status…  (Enter to send, Shift+Enter for newline)"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            disabled={loading}
          />
          <button
            className="btn btn-primary"
            onClick={() => send()}
            disabled={!input.trim() || loading}
            style={{ alignSelf:'flex-end', height:44 }}
          >
            {loading
              ? <div className="spinner" style={{width:16,height:16,borderWidth:2}}/>
              : <Send size={16}/>
            }
          </button>
        </div>
      </div>
    </div>
  );
}
