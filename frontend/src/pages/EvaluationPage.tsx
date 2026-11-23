import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Play,
  Download,
  CheckCircle2,
  XCircle,
  Clock,
  Cpu,
  History,
  AlertTriangle,
  Search,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import { evaluationService } from '../services/api';
import { EvaluationRunData } from '../types';

export const EvaluationPage: React.FC = () => {
  const [currentRun, setCurrentRun] = useState<EvaluationRunData | null>(null);
  const [history, setHistory] = useState<EvaluationRunData[]>([]);
  const [running, setRunning] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'PASSED' | 'FAILED'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const loadEvaluationData = async () => {
    try {
      const [latest, hist] = await Promise.all([
        evaluationService.getLatestResults(),
        evaluationService.getHistory(),
      ]);
      setCurrentRun(latest);
      setHistory(hist.runs || []);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadEvaluationData();
  }, []);

  const handleRunEvaluation = async () => {
    setRunning(true);
    try {
      const res = await evaluationService.runEvaluation();
      setCurrentRun(res);
      const hist = await evaluationService.getHistory();
      setHistory(hist.runs || []);
    } catch {
      // ignore
    } finally {
      setRunning(false);
    }
  };

  if (!currentRun) {
    return (
      <div className="py-16 text-center text-sm text-slate-300">
        Loading measured RAG evaluation benchmark results...
      </div>
    );
  }

  const retrievalChartData = [
    { name: 'Precision@K', score: Number((currentRun.precision_at_k * 100).toFixed(1)), threshold: (currentRun.thresholds?.precision_at_k || 0.65) * 100 },
    { name: 'Recall@K', score: Number((currentRun.recall_at_k * 100).toFixed(1)), threshold: (currentRun.thresholds?.recall_at_k || 0.75) * 100 },
    { name: 'MRR', score: Number((currentRun.mrr * 100).toFixed(1)), threshold: (currentRun.thresholds?.mrr || 0.75) * 100 },
    { name: 'Hit Rate@K', score: Number((currentRun.hit_rate_at_k * 100).toFixed(1)), threshold: 80 },
    { name: 'NDCG@K', score: Number((currentRun.ndcg_at_k * 100).toFixed(1)), threshold: (currentRun.thresholds?.ndcg_at_k || 0.75) * 100 },
  ];

  const generationChartData = [
    { name: 'Faithfulness', score: Number((currentRun.faithfulness * 100).toFixed(1)) },
    { name: 'Answer Relevancy', score: Number((currentRun.answer_relevancy * 100).toFixed(1)) },
    { name: 'Context Precision', score: Number((currentRun.context_precision * 100).toFixed(1)) },
    { name: 'Context Recall', score: Number((currentRun.context_recall * 100).toFixed(1)) },
    { name: 'Correctness', score: Number((currentRun.response_correctness * 100).toFixed(1)) },
  ];

  const categoryChartData = Object.entries(currentRun.category_breakdown || {}).map(([cat, stats]) => ({
    category: cat.replace(/_/g, ' '),
    passRate: Number((stats.pass_rate * 100).toFixed(1)),
    mrr: Number((stats.mrr * 100).toFixed(1)),
    faithfulness: Number((stats.faithfulness * 100).toFixed(1)),
  }));

  const historyLineData = [...history]
    .reverse()
    .map((r, idx) => ({
      run: `#${idx + 1} (${r.run_id.slice(-4)})`,
      overall: Number((r.overall_score * 100).toFixed(1)),
      mrr: Number((r.mrr * 100).toFixed(1)),
      faithfulness: Number((r.faithfulness * 100).toFixed(1)),
    }));

  const previousRun = history.length > 1 ? history[1] : currentRun;

  const filteredQuestions = (currentRun.question_results || []).filter((q) => {
    if (categoryFilter !== 'ALL' && q.category !== categoryFilter) return false;
    if (statusFilter === 'PASSED' && !q.passed) return false;
    if (statusFilter === 'FAILED' && q.passed) return false;
    if (searchQuery && !q.query.toLowerCase().includes(searchQuery.toLowerCase()) && !q.question_id.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6 pb-16">
      {/* Header Banner */}
      <div className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-[#0B1120] p-6 lg:flex-row lg:items-center">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <BarChart3 className="h-6 w-6 text-violet-400" />
            <h1 className="text-2xl font-extrabold text-white">
              RAG & Generation Quality Evaluation Dashboard
            </h1>
            <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-bold text-amber-300">
              Synthetic Labeled Ground-Truth Benchmark ({currentRun.total_questions} Queries)
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Run ID: <span className="font-mono text-violet-300">{currentRun.run_id}</span> • Dataset:{' '}
            {currentRun.dataset_name} • Actual Measured Pipeline Telemetry
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleRunEvaluation}
            disabled={running}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-violet-600/25 transition hover:brightness-110 disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            {running ? 'Executing 106-Query Evaluation...' : 'Run Full Evaluation Suite'}
          </button>

          <a
            href={evaluationService.getReportDownloadUrl(currentRun.run_id, 'csv')}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-xs font-bold text-slate-200 hover:border-violet-500"
          >
            <Download className="h-3.5 w-3.5 text-emerald-400" />
            Download CSV
          </a>

          <a
            href={evaluationService.getReportDownloadUrl(currentRun.run_id, 'json')}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-xs font-bold text-slate-200 hover:border-blue-500"
          >
            <Download className="h-3.5 w-3.5 text-blue-400" />
            Download JSON
          </a>
        </div>
      </div>

      {/* Primary KPI Metric Cards with Pass/Fail Threshold Badges */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {[
          {
            label: 'Overall RAG Score',
            val: `${(currentRun.overall_score * 100).toFixed(1)}%`,
            sub: `${currentRun.passed_questions}/${currentRun.total_questions} Passed`,
            passed: currentRun.overall_score >= 0.80,
          },
          {
            label: 'Precision@K / Recall@K',
            val: `${(currentRun.precision_at_k * 100).toFixed(1)}% / ${(currentRun.recall_at_k * 100).toFixed(1)}%`,
            sub: `Threshold: >=${((currentRun.thresholds?.recall_at_k || 0.75) * 100).toFixed(0)}%`,
            passed: currentRun.metric_pass_status?.recall_at_k ?? true,
          },
          {
            label: 'MRR & NDCG@K',
            val: `${(currentRun.mrr * 100).toFixed(1)}% / ${(currentRun.ndcg_at_k * 100).toFixed(1)}%`,
            sub: `Hit Rate: ${(currentRun.hit_rate_at_k * 100).toFixed(1)}%`,
            passed: currentRun.metric_pass_status?.mrr ?? true,
          },
          {
            label: 'Faithfulness Score',
            val: `${(currentRun.faithfulness * 100).toFixed(1)}%`,
            sub: `Threshold: >=${((currentRun.thresholds?.faithfulness || 0.85) * 100).toFixed(0)}%`,
            passed: currentRun.metric_pass_status?.faithfulness ?? true,
          },
          {
            label: 'Answer Relevancy',
            val: `${(currentRun.answer_relevancy * 100).toFixed(1)}%`,
            sub: `Correctness: ${(currentRun.response_correctness * 100).toFixed(1)}%`,
            passed: currentRun.metric_pass_status?.answer_relevancy ?? true,
          },
          {
            label: 'Hallucination Rate',
            val: `${(currentRun.hallucination_rate * 100).toFixed(1)}%`,
            sub: `Max Allowed: <=${((currentRun.thresholds?.max_hallucination_rate || 0.10) * 100).toFixed(0)}%`,
            passed: currentRun.metric_pass_status?.hallucination_rate ?? true,
          },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-2xl border border-slate-800 bg-[#0B1120] p-4"
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                {kpi.label}
              </span>
              {kpi.passed ? (
                <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-bold text-emerald-400">
                  PASS
                </span>
              ) : (
                <span className="rounded bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-bold text-rose-400">
                  FAIL
                </span>
              )}
            </div>
            <div className="text-xl font-extrabold text-white">{kpi.val}</div>
            <div className="mt-1 text-[11px] text-slate-400">{kpi.sub}</div>
          </div>
        ))}
      </div>

      {/* Latency, Token Usage & Before/After Run Comparison */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
            <Clock className="h-4 w-4" />
            Latency & Performance Telemetry
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="rounded-xl bg-slate-900 p-3">
              <div className="text-xs text-slate-400">Avg Total</div>
              <div className="mt-1 text-base font-extrabold text-white">
                {currentRun.avg_latency_ms.toFixed(1)} ms
              </div>
            </div>
            <div className="rounded-xl bg-slate-900 p-3">
              <div className="text-xs text-slate-400">Retrieval</div>
              <div className="mt-1 text-base font-extrabold text-violet-300">
                {currentRun.avg_retrieval_latency_ms.toFixed(1)} ms
              </div>
            </div>
            <div className="rounded-xl bg-slate-900 p-3">
              <div className="text-xs text-slate-400">Generation</div>
              <div className="mt-1 text-base font-extrabold text-blue-300">
                {currentRun.avg_generation_latency_ms.toFixed(1)} ms
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-violet-400">
            <Cpu className="h-4 w-4" />
            Token Usage & Estimated Cost
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="rounded-xl bg-slate-900 p-3">
              <div className="text-xs text-slate-400">Total Tokens</div>
              <div className="mt-1 text-base font-extrabold text-white">
                {currentRun.total_tokens.toLocaleString()}
              </div>
            </div>
            <div className="rounded-xl bg-slate-900 p-3">
              <div className="text-xs text-slate-400">Est. Cost</div>
              <div className="mt-1 text-base font-extrabold text-emerald-400">
                ${currentRun.estimated_cost_usd.toFixed(4)}
              </div>
            </div>
            <div className="rounded-xl bg-slate-900 p-3">
              <div className="text-xs text-slate-400">Hit Success</div>
              <div className="mt-1 text-base font-extrabold text-cyan-300">
                {(currentRun.retrieval_success_rate * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
            <History className="h-4 w-4" />
            Before vs After Run Comparison ({previousRun.run_id} → {currentRun.run_id})
          </div>
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-xl bg-slate-900 p-3">
              <div className="text-slate-400">Overall Score</div>
              <div className="mt-1 font-bold text-white">
                {(previousRun.overall_score * 100).toFixed(1)}% →{' '}
                <span className="text-emerald-400">{(currentRun.overall_score * 100).toFixed(1)}%</span>
              </div>
            </div>
            <div className="rounded-xl bg-slate-900 p-3">
              <div className="text-slate-400">MRR</div>
              <div className="mt-1 font-bold text-white">
                {(previousRun.mrr * 100).toFixed(1)}% →{' '}
                <span className="text-violet-300">{(currentRun.mrr * 100).toFixed(1)}%</span>
              </div>
            </div>
            <div className="rounded-xl bg-slate-900 p-3">
              <div className="text-slate-400">Faithfulness</div>
              <div className="mt-1 font-bold text-white">
                {(previousRun.faithfulness * 100).toFixed(1)}% →{' '}
                <span className="text-blue-300">{(currentRun.faithfulness * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recharts Visualizations */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <h3 className="mb-4 text-sm font-bold text-white">
            Retrieval Quality Metrics vs Configured Pass Thresholds (%)
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={retrievalChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="#94A3B8" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0B1120', borderColor: '#334155', fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="score" name="Measured Score (%)" fill="#8B5CF6" radius={[6, 6, 0, 0]} />
                <Bar dataKey="threshold" name="Min Threshold (%)" fill="#334155" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <h3 className="mb-4 text-sm font-bold text-white">
            RAGAS / DeepEval Generation Grounding Metrics (%)
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={generationChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="#94A3B8" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0B1120', borderColor: '#334155', fontSize: '12px' }}
                />
                <Bar dataKey="score" name="Measured Score (%)" fill="#3B82F6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Category Breakdown & Run History Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <h3 className="mb-4 text-sm font-bold text-white">
            Performance Across All 10 Evaluation Benchmark Categories (%)
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="category" stroke="#94A3B8" fontSize={10} angle={-20} textAnchor="end" height={55} />
                <YAxis domain={[0, 100]} stroke="#94A3B8" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0B1120', borderColor: '#334155', fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="passRate" name="Pass Rate (%)" fill="#10B981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="faithfulness" name="Faithfulness (%)" fill="#06B6D4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <h3 className="mb-4 text-sm font-bold text-white">
            Evaluation Run History Over Time ({history.length} Stored Runs)
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyLineData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="run" stroke="#94A3B8" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="#94A3B8" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0B1120', borderColor: '#334155', fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Line type="monotone" dataKey="overall" name="Overall Score (%)" stroke="#8B5CF6" strokeWidth={2.5} />
                <Line type="monotone" dataKey="mrr" name="MRR (%)" stroke="#10B981" strokeWidth={2} />
                <Line type="monotone" dataKey="faithfulness" name="Faithfulness (%)" stroke="#3B82F6" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Question-Level Results & Failed Test Case Inspector */}
      <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
        <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-base font-bold text-white">
              Detailed Question-Level Evaluation Explorer ({filteredQuestions.length} Shown)
            </h2>
            <p className="text-xs text-slate-400">
              Filter by category or inspect any failed test cases with expected vs retrieved product IDs
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5">
              <Search className="mr-1.5 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search question..."
                className="bg-transparent text-xs text-white focus:outline-none"
              />
            </div>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-white"
            >
              <option value="ALL">All 10 Categories</option>
              {Object.keys(currentRun.category_breakdown || {}).map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            <div className="flex rounded-xl border border-slate-700 bg-slate-900 p-0.5 text-xs">
              {(['ALL', 'PASSED', 'FAILED'] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`rounded-lg px-2.5 py-1 font-bold ${
                    statusFilter === st ? 'bg-violet-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="max-h-[520px] overflow-y-auto rounded-xl border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-slate-900 text-slate-400">
              <tr>
                <th className="p-3">ID & Category</th>
                <th className="p-3">Query</th>
                <th className="p-3">Expected IDs</th>
                <th className="p-3">Retrieved Top-K IDs</th>
                <th className="p-3">MRR / Recall</th>
                <th className="p-3">Faithfulness</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {filteredQuestions.map((q) => (
                <tr key={q.question_id} className="hover:bg-slate-900/50">
                  <td className="p-3 align-top">
                    <div className="font-mono font-bold text-violet-300">{q.question_id}</div>
                    <div className="text-[10px] text-slate-400">{q.category}</div>
                  </td>
                  <td className="p-3 align-top max-w-xs">
                    <div className="font-semibold text-white">{q.query}</div>
                    {q.failure_reason && (
                      <div className="mt-1 flex items-center gap-1 text-[11px] text-rose-400">
                        <AlertTriangle className="h-3 w-3" /> {q.failure_reason}
                      </div>
                    )}
                  </td>
                  <td className="p-3 align-top font-mono text-[11px] text-emerald-300">
                    {q.expected_product_ids.length > 0 ? q.expected_product_ids.join(', ') : 'NONE (Boundary)'}
                  </td>
                  <td className="p-3 align-top font-mono text-[11px] text-cyan-300">
                    {q.retrieved_product_ids.length > 0 ? q.retrieved_product_ids.slice(0, 3).join(', ') : 'NONE'}
                  </td>
                  <td className="p-3 align-top">
                    <div>MRR: {(q.mrr * 100).toFixed(0)}%</div>
                    <div className="text-slate-400">Rec: {(q.recall_at_k * 100).toFixed(0)}%</div>
                  </td>
                  <td className="p-3 align-top">
                    <div className="font-bold text-blue-300">{(q.faithfulness * 100).toFixed(0)}%</div>
                    <div className="text-[10px] text-slate-400">
                      Halluc: {(q.hallucination_rate * 100).toFixed(0)}%
                    </div>
                  </td>
                  <td className="p-3 align-top">
                    {q.passed ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-bold text-emerald-400">
                        <CheckCircle2 className="h-3.5 w-3.5" /> PASS
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-2.5 py-0.5 text-[11px] font-bold text-rose-400">
                        <XCircle className="h-3.5 w-3.5" /> FAIL
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
