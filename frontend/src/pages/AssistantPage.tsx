import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Send,
  PlusCircle,
  Trash2,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  FileText,
  ThumbsUp,
  ThumbsDown,
  Clock,
  SlidersHorizontal,
  CheckCircle2,
  Layers,
} from 'lucide-react';
import { chatService } from '../services/api';
import { ChatResponseData, Citation, ComparisonRow, Product } from '../types';
import { ProductCard } from '../components/ProductCard';

interface ChatTurn {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  recommended_products?: Product[];
  comparison_table?: ComparisonRow[] | null;
  citations?: Citation[];
  intent?: string;
  constraints?: Record<string, any>;
  rewritten_query?: string;
  confidence_score?: number;
  grounding_verified?: boolean;
  security_status?: {
    safe: boolean;
    reason: string;
    risk_category: string;
    severity: string;
  };
  latency_ms?: number;
  llm_provider?: string;
  feedback?: 'up' | 'down';
}

interface AssistantPageProps {
  compareList: string[];
  onToggleCompare: (productId: string) => void;
}

export const AssistantPage: React.FC<AssistantPageProps> = ({ compareList, onToggleCompare }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [conversations, setConversations] = useState<any[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeConstraints, setActiveConstraints] = useState<Record<string, any>>({});
  const chatEndRef = useRef<HTMLDivElement>(null);

  const suggestedPrompts = [
    'Suggest the best laptop under ₹80,000 for machine learning and programming.',
    'Recommend comfortable running shoes under ₹11,000.',
    'Show me the best winter jacket and cotton hoodie in Clothing.',
    'Suggest aesthetic room decor items under ₹7,000 like smart lamps or diffusers.',
    'Recommend tri-ply stainless steel or cast iron kitchen utensils for healthy cooking.',
    'Which headphones are best for noise cancellation?',
    'Compare the top two.',
  ];

  const loadConversationList = async () => {
    try {
      const data = await chatService.getHistory();
      setConversations(data.conversations || []);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadConversationList();
    const initialQ = searchParams.get('q');
    if (initialQ) {
      setSearchParams({});
      handleSendMessage(initialQ);
    }
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns, loading]);

  const handleSelectConversation = async (convId: string) => {
    try {
      const data = await chatService.getHistory(convId);
      setActiveConversationId(data.conversation_id);
      setActiveConstraints(data.active_constraints || {});
      const loadedTurns: ChatTurn[] = (data.messages || []).map((m: any) => ({
        id: String(m.id),
        role: m.role,
        content: m.content,
        recommended_products: m.recommended_products || [],
        citations: m.citations || [],
        intent: m.retrieval_metadata?.intent,
        constraints: m.retrieval_metadata?.constraints,
        rewritten_query: m.retrieval_metadata?.rewritten_query,
        comparison_table: m.retrieval_metadata?.comparison_table,
        latency_ms: m.retrieval_metadata?.latency_ms,
        llm_provider: m.retrieval_metadata?.llm_provider,
        confidence_score: m.confidence_score,
        grounding_verified: true,
      }));
      setTurns(loadedTurns);
    } catch {
      // ignore
    }
  };

  const handleNewConversation = () => {
    setActiveConversationId(null);
    setTurns([]);
    setActiveConstraints({});
  };

  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await chatService.deleteConversation(convId);
      if (activeConversationId === convId) {
        handleNewConversation();
      }
      loadConversationList();
    } catch {
      // ignore
    }
  };

  const handleSendMessage = async (textOverride?: string) => {
    const msg = (textOverride ?? input).trim();
    if (!msg || loading) return;
    if (!textOverride) setInput('');

    const userTurn: ChatTurn = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: msg,
    };
    setTurns((prev) => [...prev, userTurn]);
    setLoading(true);

    try {
      const res: ChatResponseData = await chatService.sendMessage(msg, activeConversationId);
      setActiveConversationId(res.conversation_id);
      setActiveConstraints(res.extracted_constraints || {});
      const assistantTurn: ChatTurn = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: res.answer,
        recommended_products: res.recommended_products,
        comparison_table: res.comparison_table,
        citations: res.citations,
        intent: res.intent,
        constraints: res.extracted_constraints,
        rewritten_query: res.rewritten_query,
        confidence_score: res.confidence_score,
        grounding_verified: res.grounding_verified,
        security_status: res.security_status,
        latency_ms: res.latency_ms,
        llm_provider: res.llm_provider,
      };
      setTurns((prev) => [...prev, assistantTurn]);
      loadConversationList();
    } catch (err: any) {
      setTurns((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: err?.response?.data?.detail || 'An error occurred communicating with the ShopMind AI RAG backend.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = (turnId: string, vote: 'up' | 'down') => {
    setTurns((prev) => prev.map((t) => (t.id === turnId ? { ...t, feedback: vote } : t)));
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      {/* Left Sidebar: Chat History & Active Constraints */}
      <aside className="space-y-4 lg:col-span-3">
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-4">
          <button
            onClick={handleNewConversation}
            className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-violet-600/25 transition hover:brightness-110"
          >
            <PlusCircle className="h-4 w-4" />
            New Shopping Session
          </button>

          <div className="mb-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Recent Conversations ({conversations.length})
          </div>
          <div className="max-h-60 space-y-1.5 overflow-y-auto pr-1">
            {conversations.length === 0 ? (
              <p className="py-3 text-xs text-slate-500">No saved conversations yet.</p>
            ) : (
              conversations.map((c) => (
                <div
                  key={c.conversation_id}
                  onClick={() => handleSelectConversation(c.conversation_id)}
                  className={`group flex cursor-pointer items-center justify-between rounded-xl px-3 py-2 text-xs transition ${
                    activeConversationId === c.conversation_id
                      ? 'border border-violet-500/40 bg-violet-600/20 text-white font-semibold'
                      : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'
                  }`}
                >
                  <span className="truncate pr-2">{c.title}</span>
                  <button
                    onClick={(e) => handleDeleteConversation(c.conversation_id, e)}
                    title="Delete Conversation"
                    className="opacity-60 hover:text-rose-400 hover:opacity-100"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Active Extracted Constraints Panel */}
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-4">
          <div className="mb-2.5 flex items-center gap-2 text-xs font-bold text-violet-300">
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Conversation State Constraints
          </div>
          {Object.keys(activeConstraints).length === 0 ? (
            <p className="text-xs text-slate-400">
              Ask a shopping question to see dynamically extracted budget, category, brand, and spec filters preserved across turns.
            </p>
          ) : (
            <div className="space-y-1.5 text-xs">
              {Object.entries(activeConstraints).map(([k, v]) => (
                <div
                  key={k}
                  className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1.5"
                >
                  <span className="font-medium capitalize text-slate-400">{k.replace(/_/g, ' ')}:</span>
                  <span className="font-bold text-cyan-300">
                    {Array.isArray(v) ? v.join(', ') : String(v)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Suggested Shopping Prompts */}
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-4">
          <div className="mb-2.5 text-xs font-bold text-slate-300">Try Grounded RAG Prompts</div>
          <div className="space-y-1.5">
            {suggestedPrompts.map((prompt) => (
              <button
                key={prompt}
                onClick={() => handleSendMessage(prompt)}
                className="w-full rounded-xl border border-slate-800/90 bg-slate-900/60 p-2.5 text-left text-[11px] leading-snug text-slate-300 transition hover:border-violet-500/50 hover:text-violet-200"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Conversational Interface */}
      <div className="flex flex-col rounded-2xl border border-slate-800 bg-[#0B1120] lg:col-span-9 min-h-[75vh]">
        {/* Header Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600/20 text-violet-400">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white">ShopMind AI Agentic RAG Assistant</h1>
              <p className="text-[11px] text-slate-400">
                Hybrid Vector + BM25 Retrieval • Grounding Verification • OWASP LLM01 Protected
              </p>
            </div>
          </div>
          {activeConversationId && (
            <span className="rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-[11px] font-mono text-slate-400">
              Session: {activeConversationId}
            </span>
          )}
        </div>

        {/* Messages Stream */}
        <div className="flex-1 space-y-6 overflow-y-auto p-5 max-h-[65vh]">
          {turns.length === 0 ? (
            <div className="my-12 text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-600/15 text-violet-400 border border-violet-500/30">
                <Sparkles className="h-7 w-7" />
              </div>
              <h2 className="mb-2 text-lg font-bold text-white">
                Ask Any Natural-Language Shopping or Product Comparison Question
              </h2>
              <p className="mx-auto mb-6 max-w-lg text-xs leading-relaxed text-slate-400">
                Every recommendation is grounded in retrieved product documents with explicit citations, confidence scores, and specification comparison tables.
              </p>
            </div>
          ) : (
            turns.map((turn) => (
              <div
                key={turn.id}
                className={`flex flex-col ${turn.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-4xl rounded-2xl p-4 ${
                    turn.role === 'user'
                      ? 'bg-gradient-to-r from-violet-600 to-blue-600 text-white shadow-lg'
                      : 'w-full border border-slate-800 bg-slate-900/75 text-slate-100'
                  }`}
                >
                  {/* Security & RAG Telemetry Badges for Assistant */}
                  {turn.role === 'assistant' && (
                    <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-slate-800 pb-2.5 text-[11px]">
                      {turn.security_status && !turn.security_status.safe ? (
                        <span className="flex items-center gap-1 rounded-full bg-rose-500/20 px-2.5 py-0.5 font-bold text-rose-300 border border-rose-500/40">
                          <ShieldAlert className="h-3.5 w-3.5" />
                          Security Block ({turn.security_status.risk_category})
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 font-semibold text-emerald-300 border border-emerald-500/30">
                          <ShieldCheck className="h-3.5 w-3.5" />
                          OWASP Guardrail Passed
                        </span>
                      )}

                      {turn.grounding_verified !== undefined && (
                        <span className="flex items-center gap-1 rounded-full bg-blue-500/15 px-2.5 py-0.5 font-semibold text-blue-300 border border-blue-500/30">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Grounding Verified
                        </span>
                      )}

                      {turn.intent && (
                        <span className="rounded-full bg-violet-500/15 px-2.5 py-0.5 font-semibold text-violet-300 border border-violet-500/30">
                          Intent: {turn.intent}
                        </span>
                      )}

                      {turn.confidence_score !== undefined && (
                        <span className="rounded-full bg-slate-800 px-2.5 py-0.5 font-semibold text-cyan-300">
                          Evidence Confidence: {(turn.confidence_score * 100).toFixed(0)}%
                        </span>
                      )}

                      {turn.latency_ms !== undefined && (
                        <span className="flex items-center gap-1 text-slate-400">
                          <Clock className="h-3 w-3" /> {turn.latency_ms.toFixed(0)} ms
                        </span>
                      )}
                    </div>
                  )}

                  {/* Formatted Text Answer */}
                  <div className="whitespace-pre-line text-sm leading-relaxed">
                    {turn.content}
                  </div>

                  {/* Inline Comparison Table when intent is product_comparison */}
                  {turn.comparison_table && turn.comparison_table.length >= 2 && (
                    <div className="mt-4 overflow-x-auto rounded-xl border border-slate-800 bg-[#070B14] p-3">
                      <div className="mb-2 text-xs font-bold text-violet-300">
                        Structured Specification & Value Comparison Matrix
                      </div>
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-400">
                            <th className="py-2 pr-3">Product</th>
                            <th className="py-2 px-3">Price</th>
                            <th className="py-2 px-3">Rating</th>
                            <th className="py-2 px-3">Key Specs</th>
                            <th className="py-2 pl-3">Value Score</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {turn.comparison_table.map((row) => (
                            <tr key={row.product_id}>
                              <td className="py-2.5 pr-3 font-bold text-white">
                                {row.name}{' '}
                                <span className="text-[11px] font-mono text-violet-400">({row.product_id})</span>
                              </td>
                              <td className="py-2.5 px-3 font-bold text-emerald-400">
                                ₹{row.price.toLocaleString('en-IN')}
                              </td>
                              <td className="py-2.5 px-3 text-amber-400">
                                {row.rating}/5 ({row.review_count})
                              </td>
                              <td className="py-2.5 px-3 text-slate-300">
                                {Object.entries(row.specifications || {})
                                  .slice(0, 3)
                                  .map(([k, v]) => `${k}: ${v}`)
                                  .join(' | ')}
                              </td>
                              <td className="py-2.5 pl-3 font-bold text-cyan-300">
                                {row.value_for_money_score}/100
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Retrieved Product Recommendation Cards */}
                  {turn.recommended_products && turn.recommended_products.length > 0 && (
                    <div className="mt-5">
                      <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-300">
                        <Layers className="h-3.5 w-3.5 text-violet-400" />
                        Grounded Product Recommendations ({turn.recommended_products.length})
                      </div>
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {turn.recommended_products.map((prod) => (
                          <ProductCard
                            key={prod.product_id}
                            product={prod}
                            compact
                            onSelectForCompare={onToggleCompare}
                            isCompared={compareList.includes(prod.product_id)}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Retrieval Evidence & Source Citations */}
                  {turn.citations && turn.citations.length > 0 && (
                    <div className="mt-4 rounded-xl border border-slate-800 bg-[#070B14]/90 p-3">
                      <div className="mb-2 flex items-center gap-1.5 text-xs font-bold text-slate-300">
                        <FileText className="h-3.5 w-3.5 text-cyan-400" />
                        Retrieved Knowledge Base Citations & Hybrid Scores
                      </div>
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        {turn.citations.map((cit) => (
                          <div
                            key={cit.product_id}
                            className="rounded-lg border border-slate-800/90 bg-slate-900/70 p-2 text-[11px]"
                          >
                            <div className="flex items-center justify-between font-bold text-slate-200">
                              <span>
                                [{cit.citation_index}] {cit.name} ({cit.product_id})
                              </span>
                              <span className="text-emerald-400">₹{cit.price.toLocaleString('en-IN')}</span>
                            </div>
                            <div className="mt-1 flex gap-3 text-[10px] font-mono text-slate-400">
                              <span>Dense: {cit.dense_score.toFixed(3)}</span>
                              <span>BM25: {cit.bm25_score.toFixed(3)}</span>
                              <span className="text-violet-300">Rerank: {cit.rerank_score.toFixed(3)}</span>
                            </div>
                            <p className="mt-1 line-clamp-2 text-[11px] text-slate-400">
                              {cit.evidence_snippet}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Assistant Footer: Provider & Feedback Buttons */}
                  {turn.role === 'assistant' && (
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-2.5 text-[11px] text-slate-400">
                      <span>Engine: {turn.llm_provider || 'ShopMind Grounded RAG'}</span>
                      <div className="flex items-center gap-2">
                        <span>Helpful?</span>
                        <button
                          onClick={() => handleFeedback(turn.id, 'up')}
                          className={`rounded p-1 ${
                            turn.feedback === 'up' ? 'bg-emerald-500/20 text-emerald-400' : 'hover:text-white'
                          }`}
                        >
                          <ThumbsUp className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleFeedback(turn.id, 'down')}
                          className={`rounded p-1 ${
                            turn.feedback === 'down' ? 'bg-rose-500/20 text-rose-400' : 'hover:text-white'
                          }`}
                        >
                          <ThumbsDown className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-xs text-slate-300">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-violet-400 border-t-transparent" />
              Executing OWASP security inspection → Hybrid FAISS + BM25 retrieval → Cross-feature reranking → Grounded synthesis...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Box */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="border-t border-slate-800 p-4"
        >
          <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 focus-within:border-violet-500">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about products, budgets, comparisons, or follow up on your preferences..."
              className="w-full bg-transparent text-sm text-white placeholder-slate-400 focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2 text-xs font-bold text-white shadow-md transition hover:brightness-110 disabled:opacity-40"
            >
              <Send className="h-3.5 w-3.5" />
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
