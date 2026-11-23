import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Plus,
  Star,
  Award,
} from 'lucide-react';
import { productService } from '../services/api';
import { ComparisonRow, Product } from '../types';

interface ComparisonPageProps {
  compareList: string[];
  setCompareList: React.Dispatch<React.SetStateAction<string[]>>;
}

export const ComparisonPage: React.FC<ComparisonPageProps> = ({ compareList, setCompareList }) => {
  const [allProducts, setAllProducts] = useState<Product[]>([]);
  const [comparisonRows, setComparisonRows] = useState<ComparisonRow[]>([]);
  const [specKeys, setSpecKeys] = useState<string[]>([]);
  const [aiSummary, setAiSummary] = useState('');
  const [llmProvider, setLlmProvider] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedAddId, setSelectedAddId] = useState('');

  useEffect(() => {
    productService
      .listProducts()
      .then((res) => setAllProducts(res.products || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (compareList.length >= 2) {
      runComparison(compareList);
    } else {
      setComparisonRows([]);
      setAiSummary('');
    }
  }, [compareList]);

  const runComparison = async (ids: string[]) => {
    setLoading(true);
    try {
      const data = await productService.compareProducts(ids.slice(0, 4));
      setComparisonRows(data.comparison_table || []);
      setSpecKeys(data.spec_keys || []);
      setAiSummary(data.ai_summary || '');
      setLlmProvider(data.llm_provider || '');
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleAddProduct = () => {
    if (!selectedAddId) return;
    if (compareList.includes(selectedAddId)) return;
    if (compareList.length >= 4) return;
    setCompareList((prev) => [...prev, selectedAddId]);
    setSelectedAddId('');
  };

  const loadPresetComparison = (ids: string[]) => {
    setCompareList(ids);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Selector Bar */}
      <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div>
            <div className="flex items-center gap-2">
              <GitCompare className="h-5 w-5 text-violet-400" />
              <h1 className="text-2xl font-extrabold text-white">
                Multi-Product Grounded Matrix Comparison (Up to 4 Products)
              </h1>
            </div>
            <p className="mt-1 text-xs text-slate-400">
              Side-by-side comparison of price, verified specifications, pros & cons, value scores, and an AI-generated grounded summary
            </p>
          </div>

          {/* Preset Quick Comparisons */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => loadPresetComparison(['PROD-LAP-001', 'PROD-LAP-002', 'PROD-LAP-007'])}
              className="rounded-xl border border-violet-500/40 bg-violet-500/10 px-3 py-1.5 text-xs font-bold text-violet-300 hover:bg-violet-500/20"
            >
              Preset: ML Laptops (3)
            </button>
            <button
              onClick={() => loadPresetComparison(['PROD-PHN-001', 'PROD-PHN-002', 'PROD-PHN-006', 'PROD-PHN-003'])}
              className="rounded-xl border border-blue-500/40 bg-blue-500/10 px-3 py-1.5 text-xs font-bold text-blue-300 hover:bg-blue-500/20"
            >
              Preset: Flagship Phones (4)
            </button>
            <button
              onClick={() => loadPresetComparison(['PROD-AUD-001', 'PROD-AUD-002', 'PROD-AUD-003'])}
              className="rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-bold text-cyan-300 hover:bg-cyan-500/20"
            >
              Preset: Premium ANC Headphones (3)
            </button>
          </div>
        </div>

        {/* Add Product Selector */}
        <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-slate-800 pt-4">
          <select
            value={selectedAddId}
            onChange={(e) => setSelectedAddId(e.target.value)}
            className="flex-1 min-w-[260px] rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-violet-500 focus:outline-none"
          >
            <option value="">Select a product from catalog to add to comparison ({compareList.length}/4)...</option>
            {allProducts.map((p) => (
              <option key={p.product_id} value={p.product_id} disabled={compareList.includes(p.product_id)}>
                [{p.category}] {p.name} ({p.product_id}) — ₹{p.price.toLocaleString('en-IN')}
              </option>
            ))}
          </select>
          <button
            onClick={handleAddProduct}
            disabled={!selectedAddId || compareList.length >= 4}
            className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-xs font-bold text-white hover:bg-violet-500 disabled:opacity-40"
          >
            <Plus className="h-4 w-4" />
            Add to Matrix
          </button>

          {compareList.length > 0 && (
            <button
              onClick={() => setCompareList([])}
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-400 hover:text-rose-400"
            >
              Clear All
            </button>
          )}
        </div>

        {/* Selected Chips */}
        <div className="mt-3 flex flex-wrap gap-2">
          {compareList.map((id) => {
            const p = allProducts.find((item) => item.product_id === id);
            return (
              <span
                key={id}
                className="flex items-center gap-2 rounded-full border border-violet-500/40 bg-violet-950/40 px-3 py-1 text-xs font-semibold text-violet-200"
              >
                {p ? p.name : id} ({id})
                <button
                  onClick={() => setCompareList((prev) => prev.filter((item) => item !== id))}
                  className="text-slate-400 hover:text-rose-400"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </span>
            );
          })}
        </div>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-12 text-center text-sm text-slate-300">
          Retrieving specification documents and generating grounded AI comparison summary...
        </div>
      ) : comparisonRows.length < 2 ? (
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-12 text-center">
          <GitCompare className="mx-auto mb-3 h-10 w-10 text-slate-500" />
          <h3 className="text-base font-bold text-white">Select at least 2 products (up to 4) to compare</h3>
          <p className="mt-1 text-xs text-slate-400">
            Use the dropdown above or click any of the 3 preset comparison bundles to inspect the side-by-side matrix.
          </p>
        </div>
      ) : (
        <>
          {/* AI-Generated Grounded Comparison Summary */}
          <div className="rounded-2xl border border-violet-500/40 bg-gradient-to-br from-violet-950/25 via-[#0B1120] to-[#0B1120] p-6">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-violet-400" />
                <h2 className="text-base font-bold text-white">
                  AI-Generated Grounded Comparison Summary
                </h2>
              </div>
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-0.5 text-[11px] font-semibold text-emerald-300">
                100% Grounded in Catalog Specs • {llmProvider}
              </span>
            </div>
            <div className="whitespace-pre-line text-sm leading-relaxed text-slate-200">
              {aiSummary}
            </div>
          </div>

          {/* Side-by-Side Matrix Table */}
          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-[#0B1120]">
            <table className="w-full min-w-[780px] text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/90">
                  <th className="w-44 p-4 font-bold uppercase tracking-wider text-slate-400">
                    Dimension
                  </th>
                  {comparisonRows.map((row) => (
                    <th key={row.product_id} className="p-4 align-top">
                      <div className="mb-2 h-32 w-full overflow-hidden rounded-xl bg-slate-950">
                        <img src={row.image_url} alt={row.name} className="h-full w-full object-cover" />
                      </div>
                      <span className="rounded bg-violet-500/20 px-1.5 py-0.5 font-mono text-[10px] text-violet-300">
                        {row.product_id}
                      </span>
                      <div className="mt-1 text-sm font-extrabold text-white">{row.name}</div>
                      <div className="text-[11px] font-semibold text-cyan-400">{row.brand}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                <tr>
                  <td className="p-4 font-bold text-slate-300">Price & Discount</td>
                  {comparisonRows.map((row) => (
                    <td key={row.product_id} className="p-4">
                      <span className="text-base font-extrabold text-emerald-400">
                        ₹{row.price.toLocaleString('en-IN')}
                      </span>
                      <span className="ml-2 rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-bold text-emerald-300">
                        {row.discount}% OFF
                      </span>
                    </td>
                  ))}
                </tr>

                <tr>
                  <td className="p-4 font-bold text-slate-300">Customer Rating</td>
                  {comparisonRows.map((row) => (
                    <td key={row.product_id} className="p-4">
                      <div className="flex items-center gap-1 font-bold text-amber-400">
                        <Star className="h-3.5 w-3.5 fill-amber-400" />
                        {row.rating} / 5.0
                        <span className="text-slate-400 font-normal">
                          ({row.review_count.toLocaleString()} reviews)
                        </span>
                      </div>
                    </td>
                  ))}
                </tr>

                <tr>
                  <td className="p-4 font-bold text-slate-300">Value for Money Score</td>
                  {comparisonRows.map((row) => (
                    <td key={row.product_id} className="p-4">
                      <div className="flex items-center gap-2">
                        <Award className="h-4 w-4 text-cyan-400" />
                        <span className="text-sm font-extrabold text-cyan-300">
                          {row.value_for_money_score} / 100
                        </span>
                      </div>
                    </td>
                  ))}
                </tr>

                {/* Dynamic Specification Rows */}
                {specKeys.map((specKey) => (
                  <tr key={specKey}>
                    <td className="p-4 font-semibold capitalize text-slate-400">
                      {specKey.replace(/_/g, ' ')}
                    </td>
                    {comparisonRows.map((row) => (
                      <td key={row.product_id} className="p-4 font-medium text-slate-200">
                        {row.specifications?.[specKey] || '—'}
                      </td>
                    ))}
                  </tr>
                ))}

                {/* Pros */}
                <tr>
                  <td className="p-4 font-bold text-emerald-400">Advantages (Pros)</td>
                  {comparisonRows.map((row) => (
                    <td key={row.product_id} className="p-4 align-top">
                      <ul className="space-y-1.5">
                        {row.pros.map((pro, i) => (
                          <li key={i} className="flex items-start gap-1.5 text-slate-200">
                            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                            <span>{pro}</span>
                          </li>
                        ))}
                      </ul>
                    </td>
                  ))}
                </tr>

                {/* Cons */}
                <tr>
                  <td className="p-4 font-bold text-amber-400">Trade-offs (Cons)</td>
                  {comparisonRows.map((row) => (
                    <td key={row.product_id} className="p-4 align-top">
                      <ul className="space-y-1.5">
                        {row.cons.map((con, i) => (
                          <li key={i} className="flex items-start gap-1.5 text-slate-400">
                            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
                            <span>{con}</span>
                          </li>
                        ))}
                      </ul>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};
