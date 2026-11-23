import React, { useState, useEffect } from 'react';
import {
  Settings,
  Upload,
  RefreshCw,
  PlusCircle,
  Activity,
  Database,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Lock,
} from 'lucide-react';
import { adminService, authService, ragService } from '../services/api';
import { User } from '../types';

interface AdminPageProps {
  user: User | null;
  setUser: (u: User | null) => void;
}

export const AdminPage: React.FC<AdminPageProps> = ({ user, setUser }) => {
  const [health, setHealth] = useState<any>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Manual product creation form state
  const [prodName, setProdName] = useState('');
  const [prodBrand, setProdBrand] = useState('');
  const [prodCategory, setProdCategory] = useState('Laptops');
  const [prodPrice, setProdPrice] = useState('');
  const [prodDesc, setProdDesc] = useState('');
  const [prodSpecs, setProdSpecs] = useState('processor: AMD Ryzen 7; ram: 16GB DDR5; storage: 1TB SSD');
  const [prodFeatures, setProdFeatures] = useState('16GB DDR5 RAM, 1TB NVMe SSD, AI Ready');

  const loadAdminData = async () => {
    try {
      const h = await adminService.getSystemHealth();
      setHealth(h);
      if (user?.role === 'admin') {
        const a = await adminService.getAnalytics();
        setAnalytics(a);
      }
    } catch (err: any) {
      // ignore if not signed in as admin yet
    }
  };

  useEffect(() => {
    loadAdminData();
  }, [user]);

  const handleQuickAdminLogin = async () => {
    setLoading(true);
    setErrorMessage('');
    try {
      const res = await authService.login('admin@shopmind.ai', 'Admin@ShopMind2026!');
      setUser(res.user);
      setStatusMessage('Authenticated as Administrator (admin@shopmind.ai).');
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || 'Admin login failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleReindex = async () => {
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const res = await ragService.reindex();
      setStatusMessage(
        `Re-indexed ${res.indexed_count} products into ${res.vector_store} (${res.vector_dimension}D) in ${res.elapsed_ms} ms.`
      );
      loadAdminData();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || 'Vector re-indexing failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const res = await adminService.uploadDataset(file);
      const job = res.ingestion_job;
      setStatusMessage(
        `Uploaded ${job.filename}: ${job.ingested_count} added, ${job.updated_count} updated, ${job.failed_count} failed. Vector store re-indexed!`
      );
      loadAdminData();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || 'Dataset upload rejected by security validator.');
    } finally {
      setLoading(false);
      e.target.value = '';
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const specsObj: Record<string, string> = {};
      prodSpecs.split(';').forEach((part) => {
        if (part.includes(':')) {
          const [k, v] = part.split(':');
          specsObj[k.trim()] = v.trim();
        }
      });
      const created = await adminService.addManualProduct({
        name: prodName,
        brand: prodBrand,
        category: prodCategory,
        price: Number(prodPrice),
        description: prodDesc,
        specifications: specsObj,
        features: prodFeatures.split(',').map((s) => s.trim()).filter(Boolean),
      });
      setStatusMessage(`Added & indexed product: ${created.name} (${created.product_id})`);
      setProdName('');
      setProdBrand('');
      setProdPrice('');
      setProdDesc('');
      loadAdminData();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || 'Failed to create product.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 pb-16">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-[#0B1120] p-6 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2.5">
            <Settings className="h-6 w-6 text-violet-400" />
            <h1 className="text-2xl font-extrabold text-white">
              Admin Operations, Data Ingestion & MLOps Control Center
            </h1>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Manage product datasets (CSV/JSON/Manual), trigger vector store re-indexing, inspect ingestion jobs, and review audit logs
          </p>
        </div>

        <div className="flex items-center gap-3">
          {user?.role !== 'admin' ? (
            <button
              onClick={handleQuickAdminLogin}
              disabled={loading}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg"
            >
              <Lock className="h-4 w-4" />
              Authenticate as Admin Architect
            </button>
          ) : (
            <button
              onClick={handleReindex}
              disabled={loading}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Re-Index Vector Knowledge Base
            </button>
          )}
        </div>
      </div>

      {statusMessage && (
        <div className="flex items-center gap-2 rounded-2xl border border-emerald-500/40 bg-emerald-950/30 p-4 text-xs font-semibold text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {statusMessage}
        </div>
      )}

      {errorMessage && (
        <div className="flex items-center gap-2 rounded-2xl border border-rose-500/40 bg-rose-950/30 p-4 text-xs font-semibold text-rose-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {errorMessage}
        </div>
      )}

      {/* System Health Overview */}
      {health && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
            <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-400">
              <span>Database Engine</span>
              <Database className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="mt-2 text-lg font-extrabold text-white">
              {health.components.database.status} ({health.components.database.engine})
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
            <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-400">
              <span>Vector Index</span>
              <Activity className="h-4 w-4 text-violet-400" />
            </div>
            <div className="mt-2 text-lg font-extrabold text-white">
              {health.components.vector_store.indexed_vectors} Vectors ({health.components.vector_store.dimension}D)
            </div>
            <div className="mt-1 truncate text-[11px] text-slate-400">
              {health.components.vector_store.embedding_backend}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
            <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-400">
              <span>Groq LLM Config</span>
              <Settings className="h-4 w-4 text-blue-400" />
            </div>
            <div className="mt-2 text-lg font-extrabold text-white">
              {health.components.llm_provider.configured_model}
            </div>
            <div className="mt-1 line-clamp-1 text-[11px] text-slate-400" title={health.components.llm_provider.mode}>
              {health.components.llm_provider.mode}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-5">
            <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-400">
              <span>Security Guardrails</span>
              <Lock className="h-4 w-4 text-cyan-400" />
            </div>
            <div className="mt-2 text-lg font-extrabold text-emerald-400">
              {health.components.security_guardrails.status}
            </div>
            <div className="mt-1 text-[11px] text-slate-400">
              Rate Limit: {health.components.security_guardrails.rate_limit_per_minute} req/min
            </div>
          </div>
        </div>
      )}

      {/* RBAC Gate Notice if not Admin */}
      {user?.role !== 'admin' ? (
        <div className="rounded-2xl border border-amber-500/40 bg-amber-950/20 p-8 text-center">
          <Lock className="mx-auto mb-3 h-8 w-8 text-amber-400" />
          <h3 className="text-base font-bold text-white">
            Administrator Role Required for Dataset Ingestion & Audit Logs
          </h3>
          <p className="mx-auto mt-1 max-w-md text-xs text-slate-300">
            Administrative endpoints (/api/admin/* and /api/rag/reindex) enforce strict JWT Role-Based Access Control.
            Click below to sign in with the pre-seeded Admin Architect credentials.
          </p>
          <button
            onClick={handleQuickAdminLogin}
            className="mt-4 rounded-xl bg-violet-600 px-5 py-2.5 text-xs font-bold text-white hover:bg-violet-500"
          >
            Sign In as Admin (admin@shopmind.ai)
          </button>
        </div>
      ) : (
        <>
          {/* Upload Dataset & Add Manual Product */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* CSV / JSON File Upload */}
            <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
              <div className="mb-3 flex items-center gap-2 text-base font-bold text-white">
                <Upload className="h-5 w-5 text-violet-400" />
                Upload Product Dataset (.CSV or .JSON)
              </div>
              <p className="mb-4 text-xs leading-relaxed text-slate-400">
                Files are validated for extension (.csv, .json), UTF-8 encoding, maximum size (10MB), price bounds, duplicate detection, and indirect prompt injection sanitization before incremental vector indexing.
              </p>

              <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-700 bg-slate-900/60 p-8 text-center transition hover:border-violet-500">
                <Upload className="mb-2 h-8 w-8 text-violet-400" />
                <span className="text-xs font-bold text-white">
                  Click to select a .CSV or .JSON product file
                </span>
                <span className="mt-1 text-[11px] text-slate-400">
                  Executables or malformed schemas are automatically blocked and logged
                </span>
                <input
                  type="file"
                  accept=".csv,.json"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>

              {analytics?.kpis && (
                <div className="mt-5 grid grid-cols-3 gap-3 text-center text-xs">
                  <div className="rounded-xl bg-slate-900 p-3">
                    <div className="text-slate-400">Catalog Size</div>
                    <div className="mt-1 text-base font-extrabold text-white">
                      {analytics.kpis.total_products}
                    </div>
                  </div>
                  <div className="rounded-xl bg-slate-900 p-3">
                    <div className="text-slate-400">Eval Runs</div>
                    <div className="mt-1 text-base font-extrabold text-violet-300">
                      {analytics.kpis.total_evaluation_runs}
                    </div>
                  </div>
                  <div className="rounded-xl bg-slate-900 p-3">
                    <div className="text-slate-400">Security Events</div>
                    <div className="mt-1 text-base font-extrabold text-cyan-300">
                      {analytics.kpis.total_security_events}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Manual Product Entry Form */}
            <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
              <div className="mb-3 flex items-center gap-2 text-base font-bold text-white">
                <PlusCircle className="h-5 w-5 text-blue-400" />
                Add Product Manually & Index Into RAG
              </div>

              <form onSubmit={handleManualSubmit} className="space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block font-semibold text-slate-300">Product Name</label>
                    <input
                      type="text"
                      required
                      value={prodName}
                      onChange={(e) => setProdName(e.target.value)}
                      placeholder="ASUS ROG Zephyrus G14"
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block font-semibold text-slate-300">Brand</label>
                    <input
                      type="text"
                      required
                      value={prodBrand}
                      onChange={(e) => setProdBrand(e.target.value)}
                      placeholder="ASUS"
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block font-semibold text-slate-300">Category</label>
                    <select
                      value={prodCategory}
                      onChange={(e) => setProdCategory(e.target.value)}
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                    >
                      <option value="Laptops">Laptops</option>
                      <option value="Smartphones">Smartphones</option>
                      <option value="Headphones">Headphones</option>
                      <option value="Smartwatches">Smartwatches</option>
                      <option value="Tablets">Tablets</option>
                      <option value="Monitors">Monitors</option>
                      <option value="Accessories">Accessories</option>
                      <option value="Shoes">Shoes</option>
                      <option value="Clothing">Clothing</option>
                      <option value="Room Decor">Room Decor</option>
                      <option value="Utensils">Utensils</option>
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block font-semibold text-slate-300">Price (₹ INR)</label>
                    <input
                      type="number"
                      required
                      min={1}
                      value={prodPrice}
                      onChange={(e) => setProdPrice(e.target.value)}
                      placeholder="89990"
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1 block font-semibold text-slate-300">Description</label>
                  <textarea
                    required
                    rows={2}
                    value={prodDesc}
                    onChange={(e) => setProdDesc(e.target.value)}
                    placeholder="Verified product overview and primary engineering/shopping use cases..."
                    className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block font-semibold text-slate-300">
                      Specifications (key: value; ...)
                    </label>
                    <input
                      type="text"
                      value={prodSpecs}
                      onChange={(e) => setProdSpecs(e.target.value)}
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block font-semibold text-slate-300">
                      Features (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={prodFeatures}
                      onChange={(e) => setProdFeatures(e.target.value)}
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 py-2.5 font-bold text-white shadow-lg"
                >
                  Ingest & Index Product
                </button>
              </form>
            </div>
          </div>

          {/* Ingestion Jobs & Audit Logs */}
          {analytics && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
                  <Database className="h-4 w-4 text-violet-400" />
                  Ingestion Job History & Failure Inspector
                </h3>
                <div className="max-h-72 space-y-2.5 overflow-y-auto pr-1 text-xs">
                  {(analytics.ingestion_jobs || []).map((job: any) => (
                    <div
                      key={job.job_id}
                      className="rounded-xl border border-slate-800 bg-slate-900/75 p-3"
                    >
                      <div className="flex items-center justify-between font-bold text-white">
                        <span>
                          {job.job_id} ({job.source_type}: {job.filename})
                        </span>
                        <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] text-emerald-300">
                          {job.status}
                        </span>
                      </div>
                      <div className="mt-1 flex gap-4 text-[11px] text-slate-400">
                        <span>Total: {job.total_records}</span>
                        <span className="text-emerald-400">Ingested: {job.ingested_count}</span>
                        <span className="text-blue-300">Updated: {job.updated_count}</span>
                        <span className="text-rose-400">Failed: {job.failed_count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-[#0B1120] p-6">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
                  <FileText className="h-4 w-4 text-cyan-400" />
                  Administrative Audit Trail
                </h3>
                <div className="max-h-72 space-y-2.5 overflow-y-auto pr-1 text-xs">
                  {(analytics.audit_logs || []).map((log: any) => (
                    <div
                      key={log.id}
                      className="rounded-xl border border-slate-800 bg-slate-900/75 p-3"
                    >
                      <div className="flex items-center justify-between font-bold text-white">
                        <span className="text-violet-300">{log.action}</span>
                        <span className="text-[11px] text-slate-400">{log.actor_email}</span>
                      </div>
                      <div className="mt-1 text-[11px] text-slate-300">
                        Resource: {log.resource_type} ({log.resource_id})
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
