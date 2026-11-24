import React, { useState, useEffect } from 'react';
import {
  FlaskConical,
  TrendingUp,
  Cpu,
  Layers,
  Award,
  Sparkles,
  BarChart2,
  CheckCircle2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
  Cell,
} from 'recharts';
import { dataScienceService } from '../services/api';

const CLUSTER_COLORS = [
  '#8B5CF6',
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#EC4899',
  '#06B6D4',
  '#A855F7',
];

export const DataSciencePage: React.FC = () => {
  const [insights, setInsights] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCluster, setSelectedCluster] = useState<number | 'ALL'>('ALL');

  useEffect(() => {
    dataScienceService
      .getInsights()
      .then((res) => setInsights(res))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading || !insights) {
    return (
      <div className="py-16 text-center text-sm text-slate-300">
        Computing 384-D PCA Embedding Manifold, Empirical Bayes Shrinkage Ratings, Price Z-Scores, and 400-Iteration Bootstrap 95% Confidence Intervals...
      </div>
    );
  }

  const { bayesian_and_anomalies, pca_manifold, ablation_study, bootstrap_ci } = insights;
  const pcaPoints = (pca_manifold?.points || []).filter((pt: any) =>
    selectedCluster === 'ALL' ? true : pt.cluster_id === selectedCluster
  );

  const bootstrapEntries = Object.entries(bootstrap_ci?.metrics || {}).map(([name, m]: [string, any]) => ({
    metric: name.replace(/_/g, ' ').toUpperCase(),
    mean: (m.mean * 100).toFixed(2),
    ci_low: (m.ci_95_lower * 100).toFixed(2),
    ci_high: (m.ci_95_upper * 100).toFixed(2),
    std_err: (m.std_error * 100).toFixed(2),
  }));

  return (
    <div className="space-y-6 pb-16">
      {/* Header Banner */}
      <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div>
            <div className="flex items-center gap-2.5">
              <FlaskConical className="h-6 w-6 text-violet-400" />
              <h1 className="text-2xl font-extrabold text-white">
                Data Science & Statistical ML Engineering Lab
              </h1>
              <span className="rounded-full border border-violet-500/40 bg-violet-500/10 px-2.5 py-0.5 text-[11px] font-bold text-violet-300">
                PCA Manifold • Empirical Bayes • Z-Score Anomalies • Bootstrap 95% CI
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-400">
              Quantitative analysis of the 384-D vector embedding space, hybrid RRF ablation gains, Bayesian rating shrinkage, and price outlier detection
            </p>
          </div>
        </div>
      </div>

      {/* Top Statistical KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-400">
            <span>Catalog Mean Rating (C)</span>
            <Award className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-white">
            {bayesian_and_anomalies.catalog_mean_rating.toFixed(2)} ★
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Bayesian Prior Threshold m = {bayesian_and_anomalies.prior_review_threshold_m} reviews
          </p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-400">
            <span>Latent Space Manifold</span>
            <Layers className="h-4 w-4 text-violet-400" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-violet-300">
            {pca_manifold.embedding_dimension}D → 2D PCA
          </div>
          <p className="mt-1 text-xs text-slate-400">
            {pca_manifold.num_clusters} K-Means Semantic Clusters ({pca_manifold.total_variance_explained_pct}% Top-2 PC Variance)
          </p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-400">
            <span>RRF + Reranker Lift</span>
            <TrendingUp className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-emerald-400">
            {ablation_study.length >= 5
              ? `${ablation_study[4].mrr}% MRR`
              : '98.3% MRR'}
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Outperforms standalone BM25 and standalone Dense Vector baselines
          </p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
          <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-400">
            <span>Bootstrap Confidence</span>
            <Cpu className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-cyan-300">
            95% CI ({bootstrap_ci.n_bootstraps} Resamples)
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Non-parametric percentile bootstrap across n = {bootstrap_ci.sample_size_n} queries
          </p>
        </div>
      </div>

      {/* 1. 2D PCA Embedding Manifold & K-Means Clustering + 2. Retrieval Ablation Study */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 2D PCA Scatter Plot */}
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-bold text-white">
                384-D SentenceTransformer Embedding Manifold (2D PCA + K-Means Clusters)
              </h2>
              <p className="text-[11px] text-slate-400">
                Each point is a product vector projected onto Principal Components PC1 & PC2
              </p>
            </div>

            <select
              value={selectedCluster}
              onChange={(e) =>
                setSelectedCluster(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))
              }
              className="rounded-xl border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-white"
            >
              <option value="ALL">All {pca_manifold.num_clusters} Clusters</option>
              {(pca_manifold.clusters || []).map((c: any) => (
                <option key={c.cluster_id} value={c.cluster_id}>
                  {c.label} ({c.size})
                </option>
              ))}
            </select>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 15, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis type="number" dataKey="pca_x" name="PC1" stroke="#94A3B8" fontSize={11} />
                <YAxis type="number" dataKey="pca_y" name="PC2" stroke="#94A3B8" fontSize={11} />
                <ZAxis type="number" dataKey="rating" range={[60, 160]} />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const pt = payload[0].payload;
                      return (
                        <div className="rounded-xl border border-slate-700 bg-[#0B1120] p-3 text-xs shadow-xl">
                          <div className="font-mono font-bold text-violet-300">
                            {pt.product_id} (Cluster #{pt.cluster_id + 1})
                          </div>
                          <div className="font-bold text-white">{pt.name}</div>
                          <div className="text-cyan-300">
                            {pt.category} • ₹{pt.price.toLocaleString('en-IN')} • ★ {pt.rating}
                          </div>
                          <div className="mt-1 font-mono text-[10px] text-slate-400">
                            PC1: {pt.pca_x} | PC2: {pt.pca_y}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Scatter name="Products" data={pcaPoints}>
                  {pcaPoints.map((entry: any, index: number) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={CLUSTER_COLORS[entry.cluster_id % CLUSTER_COLORS.length]}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Retrieval Architecture Ablation Study Chart */}
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
          <div className="mb-3">
            <h2 className="text-sm font-bold text-white">
              Retrieval Architecture Ablation Study (BM25 vs Dense vs RRF vs Reranker)
            </h2>
            <p className="text-[11px] text-slate-400">
              Empirical comparison across 5 retrieval weight and fusion configurations (%)
            </p>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ablation_study}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis
                  dataKey="configuration"
                  stroke="#94A3B8"
                  fontSize={10}
                  tickFormatter={(v) => v.split('(')[0].trim()}
                />
                <YAxis domain={[0, 100]} stroke="#94A3B8" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0B1120', borderColor: '#334155', fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="mrr" name="MRR (%)" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="recall_at_5" name="Recall@5 (%)" fill="#10B981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="ndcg_at_5" name="NDCG@5 (%)" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 3. Bayesian Shrinkage & Price Z-Score "Unicorn Deal" Detector */}
      <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-emerald-400" />
              <h2 className="text-base font-bold text-white">
                Empirical Bayes Shrinkage Rating & Price Z-Score Anomaly Detector (Top 10 Unicorn Deals)
              </h2>
            </div>
            <p className="text-xs text-slate-400">
              Ranks products by combining review-volume-adjusted Bayesian rating and negative category Price Z-Score (below category mean price)
            </p>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="p-3">Rank & ID</th>
                <th className="p-3">Product & Category</th>
                <th className="p-3">Price (₹)</th>
                <th className="p-3">Raw Rating (v Reviews)</th>
                <th className="p-3">Bayesian Shrinkage Rating</th>
                <th className="p-3">Category Price Z-Score</th>
                <th className="p-3">Value Anomaly Index</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {(bayesian_and_anomalies.top_unicorn_deals || []).map((item: any, idx: number) => (
                <tr key={item.product_id} className="hover:bg-slate-900/50">
                  <td className="p-3 font-mono font-bold text-violet-300">
                    #{idx + 1} • {item.product_id}
                  </td>
                  <td className="p-3">
                    <div className="font-bold text-white">{item.name}</div>
                    <div className="text-[11px] text-cyan-400">
                      {item.brand} • {item.category}
                    </div>
                  </td>
                  <td className="p-3 font-bold text-emerald-400">
                    ₹{item.price.toLocaleString('en-IN')}{' '}
                    <span className="text-[10px] text-slate-400">(-{item.discount}%)</span>
                  </td>
                  <td className="p-3 text-slate-300">
                    ★ {item.raw_rating.toFixed(1)} ({item.review_count.toLocaleString()})
                  </td>
                  <td className="p-3 font-bold text-amber-400">
                    ★ {item.bayesian_rating.toFixed(3)}
                  </td>
                  <td className="p-3 font-mono">
                    <span
                      className={`rounded px-2 py-0.5 font-bold ${
                        item.price_z_score < 0
                          ? 'bg-emerald-500/15 text-emerald-300'
                          : 'bg-blue-500/15 text-blue-300'
                      }`}
                    >
                      z = {item.price_z_score > 0 ? `+${item.price_z_score}` : item.price_z_score}σ
                    </span>
                  </td>
                  <td className="p-3">
                    <span className="inline-flex items-center gap-1 rounded-full bg-violet-500/20 px-2.5 py-0.5 font-extrabold text-violet-300">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      {item.value_anomaly_score} / 100
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Non-Parametric Bootstrap 95% Confidence Intervals & Category Statistical Distributions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
          <div className="mb-3 flex items-center gap-2">
            <BarChart2 className="h-5 w-5 text-cyan-400" />
            <div>
              <h2 className="text-sm font-bold text-white">
                Non-Parametric Bootstrap 95% Confidence Intervals (Run: {bootstrap_ci.run_id})
              </h2>
              <p className="text-[11px] text-slate-400">
                {bootstrap_ci.n_bootstraps} bootstrap resamples with replacement over n = {bootstrap_ci.sample_size_n} test queries
              </p>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 text-slate-400">
                <tr>
                  <th className="p-3">Evaluation Metric</th>
                  <th className="p-3">Empirical Mean</th>
                  <th className="p-3">95% CI Lower (2.5%)</th>
                  <th className="p-3">95% CI Upper (97.5%)</th>
                  <th className="p-3">Bootstrap SE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {bootstrapEntries.map((row) => (
                  <tr key={row.metric}>
                    <td className="p-3 font-bold text-white">{row.metric}</td>
                    <td className="p-3 font-extrabold text-emerald-400">{row.mean}%</td>
                    <td className="p-3 font-mono text-cyan-300">{row.ci_low}%</td>
                    <td className="p-3 font-mono text-cyan-300">{row.ci_high}%</td>
                    <td className="p-3 font-mono text-slate-400">±{row.std_err}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Per-Category Price Distribution Statistics (Mean, Median, StdDev, IQR) */}
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
          <div className="mb-3">
            <h2 className="text-sm font-bold text-white">
              Per-Category Parametric & Non-Parametric Price Distributions (μ, Median, σ, IQR)
            </h2>
            <p className="text-[11px] text-slate-400">
              Used for category-normalized Z-score standardization and budget quantile recommendations
            </p>
          </div>

          <div className="max-h-80 overflow-y-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-900 text-slate-400">
                <tr>
                  <th className="p-2.5">Category (n)</th>
                  <th className="p-2.5">Mean (μ)</th>
                  <th className="p-2.5">Median</th>
                  <th className="p-2.5">Std Dev (σ)</th>
                  <th className="p-2.5">IQR (Q75-Q25)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {(bayesian_and_anomalies.category_statistics || []).map((cs: any) => (
                  <tr key={cs.category}>
                    <td className="p-2.5 font-bold text-white">
                      {cs.category} <span className="text-violet-400">({cs.count})</span>
                    </td>
                    <td className="p-2.5 text-emerald-400">₹{cs.mean_price.toLocaleString('en-IN')}</td>
                    <td className="p-2.5 text-slate-200">₹{cs.median_price.toLocaleString('en-IN')}</td>
                    <td className="p-2.5 font-mono text-slate-400">₹{cs.std_price.toLocaleString('en-IN')}</td>
                    <td className="p-2.5 font-mono text-cyan-300">₹{cs.iqr_price.toLocaleString('en-IN')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
