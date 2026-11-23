import React from 'react';
import { Star, ExternalLink, CheckCircle2, Sparkles, GitCompare, Tag } from 'lucide-react';
import { Product } from '../types';

interface ProductCardProps {
  product: Product;
  onSelectForCompare?: (productId: string) => void;
  isCompared?: boolean;
  onViewDetails?: (product: Product) => void;
  compact?: boolean;
}

export const ProductCard: React.FC<ProductCardProps> = ({
  product,
  onSelectForCompare,
  isCompared = false,
  onViewDetails,
  compact = false,
}) => {
  const specEntries = Object.entries(product.specifications || {}).slice(0, compact ? 3 : 4);

  return (
    <div className="group relative flex flex-col justify-between rounded-2xl border border-slate-800/80 bg-[#0B1120]/90 p-4 shadow-xl transition-all duration-300 hover:-translate-y-1 hover:border-violet-500/50 hover:shadow-violet-500/10">
      <div>
        {/* Image & Badges */}
        <div className="relative mb-3 h-44 w-full overflow-hidden rounded-xl bg-slate-900">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-slate-600">No Image</div>
          )}
          <div className="absolute left-2.5 top-2.5 flex flex-wrap gap-1.5">
            <span className="rounded-full bg-slate-950/85 px-2.5 py-0.5 text-[11px] font-semibold tracking-wide text-violet-300 backdrop-blur-md border border-violet-500/30">
              {product.product_id}
            </span>
            <span className="rounded-full bg-blue-600/90 px-2.5 py-0.5 text-[11px] font-semibold text-white backdrop-blur-md">
              {product.category}
            </span>
          </div>
          {product.discount > 0 && (
            <span className="absolute right-2.5 top-2.5 flex items-center gap-1 rounded-full bg-emerald-500/90 px-2.5 py-0.5 text-[11px] font-bold text-slate-950">
              <Tag className="h-3 w-3" /> {product.discount}% OFF
            </span>
          )}
        </div>

        {/* Brand & Rating */}
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="font-semibold uppercase tracking-wider text-cyan-400">{product.brand}</span>
          <div className="flex items-center gap-1 text-amber-400">
            <Star className="h-3.5 w-3.5 fill-amber-400" />
            <span className="font-bold text-slate-100">{product.rating.toFixed(1)}</span>
            <span className="text-slate-400">({product.review_count.toLocaleString()})</span>
          </div>
        </div>

        {/* Title */}
        <h3 className="mb-2 line-clamp-2 text-base font-bold text-slate-100 group-hover:text-violet-300">
          {product.name}
        </h3>

        {/* Price & Availability */}
        <div className="mb-3 flex items-baseline justify-between">
          <div>
            <span className="text-xl font-extrabold text-white">
              ₹{product.price.toLocaleString('en-IN')}
            </span>
            {product.discount > 0 && (
              <span className="ml-2 text-xs text-slate-500 line-through">
                ₹{Math.round(product.price / (1 - product.discount / 100)).toLocaleString('en-IN')}
              </span>
            )}
          </div>
          <span className="flex items-center gap-1 text-xs font-medium text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {product.availability}
          </span>
        </div>

        {/* Key Specifications */}
        {specEntries.length > 0 && (
          <div className="mb-3 rounded-xl border border-slate-800/80 bg-slate-900/60 p-2.5 text-xs">
            <div className="mb-1.5 font-semibold text-slate-300">Verified Specifications</div>
            <div className="space-y-1">
              {specEntries.map(([key, val]) => (
                <div key={key} className="flex justify-between gap-2 text-[11px]">
                  <span className="font-medium capitalize text-slate-400">{key.replace(/_/g, ' ')}:</span>
                  <span className="truncate font-semibold text-slate-200 max-w-[65%]" title={String(val)}>
                    {String(val)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Why Recommended Grounding Explanation */}
        {product.why_recommended && (
          <div className="mb-3 rounded-xl border border-violet-500/30 bg-violet-950/25 p-2.5 text-xs text-violet-200">
            <div className="mb-1 flex items-center gap-1.5 font-bold text-violet-300">
              <Sparkles className="h-3.5 w-3.5 text-violet-400" />
              Why Recommended (RAG Grounded)
            </div>
            <p className="line-clamp-3 text-[11px] leading-relaxed text-slate-300">
              {product.why_recommended}
            </p>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="mt-2 flex items-center gap-2 border-t border-slate-800/80 pt-3">
        {onViewDetails && (
          <button
            onClick={() => onViewDetails(product)}
            className="flex-1 rounded-lg bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-700"
          >
            Inspect Specs
          </button>
        )}
        {onSelectForCompare && (
          <button
            onClick={() => onSelectForCompare(product.product_id)}
            className={`flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold transition ${
              isCompared
                ? 'bg-violet-600 text-white shadow-lg shadow-violet-600/30'
                : 'border border-slate-700 bg-slate-900 text-slate-300 hover:border-violet-500/50 hover:text-white'
            }`}
          >
            <GitCompare className="h-3.5 w-3.5" />
            {isCompared ? 'Selected' : 'Compare'}
          </button>
        )}
        <a
          href={product.product_url || `#/products?id=${product.product_id}`}
          target="_blank"
          rel="noreferrer"
          title={`Source: ${product.product_id}`}
          className="flex items-center justify-center rounded-lg border border-slate-800 bg-slate-900/90 p-2 text-slate-400 transition hover:border-blue-500/50 hover:text-blue-400"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>
    </div>
  );
};
