import { ArrowRight, Bot, LoaderCircle, RotateCcw, Send, Sparkles, UserRound } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useLocation, type Location } from "react-router-dom";
import ProductCard from "../components/ProductCard";
import { useCart } from "../context/useCart";
import { api, errorMessage } from "../services/api";
import type { AgentResponse } from "../types";

const prompts = ["A laptop under ₹60,000 for Python and college", "Wireless headphones for long flights", "A smartphone with a great camera", "Compare monitors for programming"];

export default function Assistant() {
  const location: Location & { state: { prompt?: string } | null } = useLocation();
  const [input, setInput] = useState(location.state?.prompt || "");
  type ChatMessage = {
    role: "user" | "assistant";
    text: string;
    recommendations?: AgentResponse["recommendations"];
    requirements?: AgentResponse["requirements"];
    aiWarning?: string;
  };
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const { add } = useCart();
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);
  async function send(text = input): Promise<void> {
    const query = text.trim();
    if (!query || busy) return;
    const next: ChatMessage[] = [...messages, { role: "user", text: query }];
    setMessages(next); setInput(""); setBusy(true); setError("");
    try {
      const priorContext = next.slice(-6).map((m) => `${m.role === "user" ? "Customer" : "Agent"}: ${m.text}`).join("\n");
      const { data } = await api.post<AgentResponse>("/api/agent/chat", { message: priorContext });
      setMessages((current) => [...current, {
        role: "assistant",
        text: data.response,
        recommendations: data.recommendations,
        requirements: data.requirements,
        aiWarning: data.ai_warning,
      }]);
    } catch (e) {
      setError(errorMessage(e));
      setMessages((current) => [...current, { role: "assistant", text: "I couldn't reach the product catalogue just now. Please try again in a moment.", recommendations: [] }]);
    } finally { setBusy(false); }
  }
  return <main className="assistant-page shell">
    <aside className="assistant-aside">
      <div className="agent-avatar"><Bot size={24} /><span /></div>
      <p className="eyebrow">YOUR SHOPPING AGENT</p><h1>Good choices<br />start with a chat.</h1><p className="assistant-intro">Tell me what matters most. I’ll search the real catalogue and help you compare your options.</p>
      <div className="agent-status"><span className="pulse-dot" /> Ready to help <span>·</span> Catalogue-backed</div>
      <div className="prompt-list"><span className="eyebrow">NOT SURE WHERE TO START?</span>{prompts.map((prompt) => <button key={prompt} onClick={() => send(prompt)}>{prompt}<ArrowRight size={14} /></button>)}</div>
      <div className="privacy-note"><Sparkles size={14} /> You approve every cart and checkout action.</div>
    </aside>
    <section className="chat-panel">
      <div className="chat-topbar"><div><strong>Shopping assistant</strong><small>Product discovery · Demo ratings shown</small></div><button className="icon-button" title="Clear conversation" onClick={() => { setMessages([]); setError(""); }}><RotateCcw size={16} /></button></div>
      <div className="chat-messages">
        {messages.length === 0 && <div className="chat-welcome"><div className="welcome-icon"><Sparkles size={22} /></div><p className="eyebrow">A BETTER WAY TO SHOP</p><h2>What are we looking for?</h2><p>Share your budget, what you’ll use it for, or the features you care about. We’ll find real products to match.</p><div className="welcome-prompts">{prompts.slice(0, 3).map((p) => <button key={p} onClick={() => send(p)}>{p}<ArrowRight size={14} /></button>)}</div></div>}
        {messages.map((message, index) => <div className={`message-row ${message.role}`} key={index}><div className="message-avatar">{message.role === "user" ? <UserRound size={15} /> : <Bot size={16} />}</div><div className="message-content"><div className="bubble">{message.text}</div>{message.aiWarning && <div className="inline-error" role="alert">{message.aiWarning}</div>}{message.requirements?.max_budget && <span className="intent-chip">Budget · up to ₹{Number(message.requirements.max_budget).toLocaleString("en-IN")}</span>}{Boolean(message.recommendations?.length) && <div className="recommendation-grid">{message.recommendations?.map(({ product, explanation }) => <div className="rec-wrap" key={product.id}><ProductCard product={product} onAdd={add} compact /><p className="recommendation-reason"><Sparkles size={13} /> {explanation}</p></div>)}</div>}</div></div>)}
        {busy && <div className="message-row assistant"><div className="message-avatar"><Bot size={16} /></div><div className="typing-bubble"><LoaderCircle size={16} className="spin" /> Searching the catalogue and weighing your options…</div></div>}
        {error && <div className="inline-error">{error}</div>}
        <div ref={bottomRef} />
      </div>
      <form className="chat-composer" onSubmit={(e: FormEvent<HTMLFormElement>) => { e.preventDefault(); void send(); }}><input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Tell me what you’re looking for…" aria-label="Message shopping assistant" /><button aria-label="Send message" disabled={busy || !input.trim()}><Send size={17} /></button></form>
      <p className="chat-disclaimer">Recommendations use catalogue data. Ratings shown are illustrative demo data.</p>
    </section>
  </main>;
}
