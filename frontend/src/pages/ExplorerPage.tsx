import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  RotateCcw,
  Star,
  X,
  CheckCircle2,
  GitCompare,
  Sparkles,
} from 'lucide-react';
import { productService } from '../services/api';
import { Product } from '../types';
import { ProductCard } from '../components/ProductCard';

interface ExplorerPageProps {
  compareList: string[];
  onToggleCompare: (productId: string) => void;
}

export const ExplorerPage: React.FC<ExplorerPageProps> = ({ compareList, onToggleCompare }) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [brands, setBrands] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedBrand, setSelectedBrand] = useState('All');
  const [maxPrice, setMaxPrice] = useState<number>(125000);
  const [minRating, setMinRating] = useState<number>(0);
  const [sortBy, setSortBy] = useState('rating_desc');
  const [loading, setLoading] = useState(true);
  const [activeProduct, setActiveProduct] = useState<Product | null>(null);
  const [similarProducts, setSimilarProducts] = useState<Product[]>([]);

  const fetchCatalog = async () => {
    setLoading(true);
    try {
      const data = await productService.listProducts({
        search: search || undefined,
        category: selectedCategory !== 'All' ? selectedCategory : undefined,
        brand: selectedBrand !== 'All' ? selectedBrand : undefined,
        max_price: maxPrice,
        min_rating: minRating > 0 ? minRating : undefined,
        sort_by: sortBy,
      });
      setProducts(data.products || []);
      if (categories.length === 0) setCategories(data.categories || []);
      if (brands.length === 0) setBrands(data.brands || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCatalog();
  }, [selectedCategory, selectedBrand, maxPrice, minRating, sortBy]);

  const handleOpenProductModal = async (product: Product) => {
    setActiveProduct(product);
    try {
      const simRes = await productService.recommendProducts({
        similar_to_product_id: product.product_id,
        top_k: 3,
      });
      setSimilarProducts(simRes.recommendations || []);
    } catch {
      setSimilarProducts([]);
    }
  };

  const resetFilters = () => {
    setSearch('');
    setSelectedCategory('All');
    setSelectedBrand('All');
    setMaxPrice(125000);
    setMinRating(0);
    setSortBy('rating_desc');
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Search */}
      <div className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-[#0B1120] p-6 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-extrabold text-white">Verified Product Knowledge Base Explorer</h1>
          <p className="text-xs text-slate-400">
            Browse all {products.length} indexed products with full technical specifications and RAG vector metadata
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            fetchCatalog();
          }}
          className="flex w-full max-w-md items-center gap-2"
        >
          <div className="flex flex-1 items-center rounded-xl border border-slate-700 bg-slate-900 px-3 py-2">
            <Search className="mr-2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name, brand, GPU, processor, or ID..."
              className="w-full bg-transparent text-xs text-white focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="rounded-xl bg-violet-600 px-4 py-2 text-xs font-bold text-white hover:bg-violet-500"
          >
            Search
          </button>
        </form>
      </div>

      {/* Filter Controls Bar */}
      <div className="grid grid-cols-1 gap-4 rounded-2xl border border-slate-800 bg-[#0B1120] p-4 sm:grid-cols-2 lg:grid-cols-5">
        <div>
          <label className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Category
          </label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-violet-500 focus:outline-none"
          >
            <option value="All">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Brand
          </label>
          <select
            value={selectedBrand}
            onChange={(e) => setSelectedBrand(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-violet-500 focus:outline-none"
          >
            <option value="All">All Brands</option>
            {brands.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 flex justify-between text-[11px] font-bold uppercase tracking-wider text-slate-400">
            <span>Max Budget</span>
            <span className="text-violet-300">₹{maxPrice.toLocaleString('en-IN')}</span>
          </label>
          <input
            type="range"
            min={5000}
            max={125000}
            step={5000}
            value={maxPrice}
            onChange={(e) => setMaxPrice(Number(e.target.value))}
            className="w-full accent-violet-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Minimum Rating
          </label>
          <select
            value={minRating}
            onChange={(e) => setMinRating(Number(e.target.value))}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-violet-500 focus:outline-none"
          >
            <option value={0}>Any Rating</option>
            <option value={4.5}>4.5 ★ & Above</option>
            <option value={4.7}>4.7 ★ & Above</option>
            <option value={4.8}>4.8 ★ & Above</option>
          </select>
        </div>

        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-violet-500 focus:outline-none"
            >
              <option value="rating_desc">Highest Rated</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="reviews_desc">Most Reviewed</option>
            </select>
          </div>
          <button
            onClick={resetFilters}
            title="Reset Filters"
            className="rounded-xl border border-slate-700 bg-slate-900 p-2 text-slate-300 hover:border-violet-500 hover:text-white"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Product Grid */}
      {loading ? (
        <div className="py-16 text-center text-sm text-slate-400">Loading product knowledge base...</div>
      ) : products.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-[#0B1120] py-16 text-center">
          <Filter className="mx-auto mb-3 h-8 w-8 text-slate-500" />
          <p className="text-sm font-bold text-white">No products match these filter constraints</p>
          <button
            onClick={resetFilters}
            className="mt-3 rounded-xl bg-violet-600 px-4 py-2 text-xs font-bold text-white"
          >
            Reset All Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {products.map((prod) => (
            <ProductCard
              key={prod.product_id}
              product={prod}
              onSelectForCompare={onToggleCompare}
              isCompared={compareList.includes(prod.product_id)}
              onViewDetails={handleOpenProductModal}
            />
          ))}
        </div>
      )}

      {/* Product Detail & Similar Products Modal */}
      {activeProduct && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="relative max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl">
            <button
              onClick={() => setActiveProduct(null)}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="overflow-hidden rounded-xl bg-slate-900">
                <img
                  src={activeProduct.image_url}
                  alt={activeProduct.name}
                  className="h-64 w-full object-cover"
                />
              </div>

              <div>
                <div className="mb-2 flex items-center gap-2">
                  <span className="rounded-md bg-violet-500/20 px-2 py-0.5 text-xs font-mono font-bold text-violet-300">
                    {activeProduct.product_id}
                  </span>
                  <span className="rounded-md bg-blue-500/20 px-2 py-0.5 text-xs font-bold text-blue-300">
                    {activeProduct.category}
                  </span>
                  <span className="text-xs font-bold uppercase text-cyan-400">{activeProduct.brand}</span>
                </div>

                <h2 className="mb-2 text-xl font-extrabold text-white">{activeProduct.name}</h2>

                <div className="mb-3 flex items-center gap-4">
                  <span className="text-2xl font-extrabold text-emerald-400">
                    ₹{activeProduct.price.toLocaleString('en-IN')}
                  </span>
                  <span className="flex items-center gap-1 text-xs font-bold text-amber-400">
                    <Star className="h-4 w-4 fill-amber-400" />
                    {activeProduct.rating} ({activeProduct.review_count.toLocaleString()} reviews)
                  </span>
                  <span className="flex items-center gap-1 text-xs text-emerald-400">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {activeProduct.availability}
                  </span>
                </div>

                <p className="mb-4 text-xs leading-relaxed text-slate-300">{activeProduct.description}</p>

                <div className="mb-4 flex flex-wrap gap-1.5">
                  {(activeProduct.features || []).map((f) => (
                    <span
                      key={f}
                      className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-violet-200"
                    >
                      {f}
                    </span>
                  ))}
                </div>

                <button
                  onClick={() => onToggleCompare(activeProduct.product_id)}
                  className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2 text-xs font-bold text-white"
                >
                  <GitCompare className="h-4 w-4" />
                  {compareList.includes(activeProduct.product_id)
                    ? 'Remove from Comparison Tray'
                    : 'Add to Comparison Tray'}
                </button>
              </div>
            </div>

            {/* Complete Specifications Table */}
            <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900/70 p-4">
              <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-300">
                Complete Technical Specifications
              </h3>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {Object.entries(activeProduct.specifications || {}).map(([k, v]) => (
                  <div
                    key={k}
                    className="flex justify-between rounded-lg border border-slate-800 bg-[#070B14] px-3 py-2 text-xs"
                  >
                    <span className="font-semibold capitalize text-slate-400">{k.replace(/_/g, ' ')}</span>
                    <span className="font-bold text-slate-100 text-right max-w-[65%]">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Vector-Retrieved Similar Products */}
            {similarProducts.length > 0 && (
              <div className="mt-6">
                <div className="mb-3 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-violet-300">
                  <Sparkles className="h-3.5 w-3.5" />
                  RAG Vector-Similar Alternatives in {activeProduct.category}
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {similarProducts.map((sim) => (
                    <div
                      key={sim.product_id}
                      onClick={() => handleOpenProductModal(sim)}
                      className="cursor-pointer rounded-xl border border-slate-800 bg-slate-900/80 p-3 transition hover:border-violet-500/50"
                    >
                      <div className="text-[11px] font-mono text-violet-400">{sim.product_id}</div>
                      <div className="line-clamp-1 text-xs font-bold text-white">{sim.name}</div>
                      <div className="mt-1 flex items-center justify-between text-xs">
                        <span className="font-bold text-emerald-400">₹{sim.price.toLocaleString('en-IN')}</span>
                        <span className="text-amber-400">★ {sim.rating}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
