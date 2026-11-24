"""Data Science & Statistical ML Engine for ShopMind AI.

Implements:
1. Empirical Bayes Shrinkage Rating (IMDb Weighted Rating formula: (v/(v+m))*R + (m/(v+m))*C)
2. Per-Category Price Z-Scores, IQR distributions, and Value-Anomaly Bargain Index
3. 384-D -> 2D PCA / TruncatedSVD Embedding Manifold Projection & K-Means Semantic Clustering
4. Hybrid Retrieval Weight Ablation & Grid-Search Study (Dense alpha vs BM25 beta vs RRF k)
5. Non-Parametric Bootstrap 95% Confidence Intervals for RAG Evaluation Metrics
"""
# This calculate the statistical analytics and ML experiments for ShopMind's product catalog and RAG retrieval system.
import math
from collections import defaultdict
from typing import Any, Dict, List
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sqlalchemy.orm import Session
from app.models.models import EvaluationRun
from app.rag.pipeline import _tokenize, rag_engine

# this function is used to compute the statistical analytics and ML experiments for ShopMind's product catalog and RAG retrieval system.
class DataScienceEngine:
    """Computes statistical product analytics, embedding manifold projections, and retrieval ablation experiments."""

    @staticmethod
    def compute_bayesian_ratings_and_anomalies(products: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not products:
            return {"catalog_mean_rating": 0.0, "prior_m": 500, "enriched_products": [], "category_stats": []}

        ratings = np.array([float(p["rating"]) for p in products], dtype=np.float64)
        reviews = np.array([float(p["review_count"]) for p in products], dtype=np.float64)

        # Catalog global mean rating (C) and 25th-percentile review count prior (m)
        c_mean = float(np.mean(ratings))
        m_prior = float(np.percentile(reviews, 35)) if len(reviews) > 0 else 500.0

        # Group prices by category for Z-score and IQR calculation
        cat_prices: Dict[str, List[float]] = defaultdict(list)
        cat_ratings: Dict[str, List[float]] = defaultdict(list)
        for p in products:
            cat_prices[p["category"]].append(float(p["price"]))
            cat_ratings[p["category"]].append(float(p["rating"]))

        cat_summary: Dict[str, Dict[str, float]] = {}
        for cat, p_list in cat_prices.items():
            arr = np.array(p_list, dtype=np.float64)
            r_arr = np.array(cat_ratings[cat], dtype=np.float64)
            mean_p = float(np.mean(arr))
            std_p = float(np.std(arr)) if len(arr) > 1 and np.std(arr) > 0 else 1.0
            q25, median_p, q75 = [float(x) for x in np.percentile(arr, [25, 50, 75])]
            cat_summary[cat] = {
                "category": cat,
                "count": len(p_list),
                "mean_price": round(mean_p, 2),
                "median_price": round(median_p, 2),
                "std_price": round(std_p, 2),
                "iqr_price": round(q75 - q25, 2),
                "min_price": round(float(np.min(arr)), 2),
                "max_price": round(float(np.max(arr)), 2),
                "mean_rating": round(float(np.mean(r_arr)), 3),
            }

        enriched: List[Dict[str, Any]] = []
        for p in products:
            v = float(p["review_count"])
            r = float(p["rating"])
            bayesian_r = (v / (v + m_prior)) * r + (m_prior / (v + m_prior)) * c_mean

            c_info = cat_summary[p["category"]]
            z_price = (float(p["price"]) - c_info["mean_price"]) / max(1.0, c_info["std_price"])

            # Value Anomaly Score: High Bayesian rating + negative price Z-score (below category mean) + high discount
            value_anomaly_score = round(
                (bayesian_r / 5.0) * 60.0
                + (max(-2.0, min(2.0, -z_price)) + 2.0) * 7.5
                + (float(p.get("discount", 0.0)) / 40.0) * 10.0,
                2,
            )

            enriched.append(
                {
                    "product_id": p["product_id"],
                    "name": p["name"],
                    "brand": p["brand"],
                    "category": p["category"],
                    "price": p["price"],
                    "discount": p.get("discount", 0.0),
                    "raw_rating": r,
                    "review_count": int(v),
                    "bayesian_rating": round(float(bayesian_r), 4),
                    "price_z_score": round(float(z_price), 3),
                    "value_anomaly_score": value_anomaly_score,
                    "is_unicorn_deal": bool(z_price <= -0.35 and bayesian_r >= c_mean),
                }
            )

        enriched.sort(key=lambda x: x["value_anomaly_score"], reverse=True)
        return {
            "catalog_mean_rating": round(c_mean, 4),
            "prior_review_threshold_m": round(m_prior, 1),
            "top_unicorn_deals": enriched[:10],
            "all_scored_products": enriched,
            "category_statistics": list(cat_summary.values()),
        }

# This function is used to compute the embedding manifold projection and clustering for ShopMind's product embeddings.

    @staticmethod
    def compute_embedding_manifold_pca(db: Session, n_clusters: int = 7) -> Dict[str, Any]:
        """Projects 384-D product embeddings to 2D via PCA and runs K-Means clustering in latent space."""
        rag_engine.ensure_initialized(db)
        chunks = rag_engine.document_chunks
        products = rag_engine.products_cache
        if len(chunks) < 3:
            return {"explained_variance_ratio": [0.0, 0.0], "points": [], "clusters": []}

        embeddings = rag_engine.embedder.fit_corpus(chunks)
        pca = PCA(n_components=2, random_state=42)
        coords_2d = pca.fit_transform(embeddings)

        k = min(n_clusters, len(products))
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        cluster_ids = kmeans.fit_predict(embeddings)

        points: List[Dict[str, Any]] = []
        cluster_groups: Dict[int, List[str]] = defaultdict(list)

        for idx, p in enumerate(products):
            cid = int(cluster_ids[idx])
            cluster_groups[cid].append(p["category"])
            points.append(
                {
                    "product_id": p["product_id"],
                    "name": p["name"],
                    "brand": p["brand"],
                    "category": p["category"],
                    "price": p["price"],
                    "rating": p["rating"],
                    "pca_x": round(float(coords_2d[idx, 0]), 4),
                    "pca_y": round(float(coords_2d[idx, 1]), 4),
                    "cluster_id": cid,
                }
            )

        cluster_summaries = []
        for cid, cats in sorted(cluster_groups.items()):
            dominant_cat = max(set(cats), key=cats.count)
            cluster_summaries.append(
                {
                    "cluster_id": cid,
                    "label": f"Cluster #{cid + 1}: {dominant_cat} Manifold",
                    "size": len(cats),
                    "dominant_category": dominant_cat,
                }
            )

        return {
            "embedding_dimension": int(embeddings.shape[1]),
            "reduced_dimension": 2,
            "explained_variance_ratio": [round(float(x), 4) for x in pca.explained_variance_ratio_],
            "total_variance_explained_pct": round(float(np.sum(pca.explained_variance_ratio_)) * 100.0, 2),
            "num_clusters": k,
            "clusters": cluster_summaries,
            "points": points,
        }

# this function is used to compute the retrieval ablation study for ShopMind's RAG retrieval system.
# retrival ablation study is a systematic evaluation of different retrieval architectures to understand their performance and contribution to the overall retrieval system. It helps identify the strengths and weaknesses of each architecture and informs decisions for optimizing the retrieval process.

    @staticmethod
    def run_retrieval_ablation_study(db: Session) -> List[Dict[str, Any]]:
        """Runs a systematic ablation study across 5 retrieval architectures on a fast 30-query stratified benchmark slice."""
        rag_engine.ensure_initialized(db)
        from app.evaluation.evaluator import RAGEvaluator

        dataset = RAGEvaluator.load_evaluation_dataset()
        all_qs = [q for q in dataset.get("questions", []) if q.get("relevant_product_ids")]
        sample_qs = all_qs[:30]

        if not sample_qs or not rag_engine.products_cache:
            return []

        num_docs = len(rag_engine.products_cache)
        configs = [
            {"name": "1. Sparse BM25 Only (alpha=0.0, beta=1.0)", "alpha": 0.0, "beta": 1.0, "use_rrf": False, "use_reranker": False},
            {"name": "2. Dense Vector Only (alpha=1.0, beta=0.0)", "alpha": 1.0, "beta": 0.0, "use_rrf": False, "use_reranker": False},
            {"name": "3. Linear Hybrid (alpha=0.55, beta=0.45)", "alpha": 0.55, "beta": 0.45, "use_rrf": False, "use_reranker": False},
            {"name": "4. Hybrid + RRF Fusion (k=20)", "alpha": 0.55, "beta": 0.45, "use_rrf": True, "use_reranker": False},
            {"name": "5. ShopMind Production (Hybrid + RRF + Cross-Feature Reranker)", "alpha": 0.55, "beta": 0.45, "use_rrf": True, "use_reranker": True},
        ]

        ablation_results = []
        for cfg in configs:
            mrr_sum = 0.0
            recall_sum = 0.0
            ndcg_sum = 0.0

            for q_item in sample_qs:
                query = q_item["query"]
                expected_set = set(q_item["relevant_product_ids"])

                if cfg["use_reranker"]:
                    res = rag_engine.hybrid_retrieve(db=db, query=query, top_k=5, use_reranker=True)
                    top_ids = [r["product_id"] for r in res["results"][:5]]
                else:
                    q_vec = rag_engine.embedder.encode_query(query)
                    d_raw, d_idx = rag_engine.faiss_index.search(q_vec, num_docs)
                    dense_scores = np.zeros(num_docs, dtype=np.float32)
                    for pos, did in enumerate(d_idx[0]):
                        if 0 <= did < num_docs:
                            dense_scores[did] = max(0.0, float(d_raw[0][pos]))
                    bm25_scores = rag_engine.bm25.score_all(query)

                    d_order = np.argsort(-dense_scores)
                    b_order = np.argsort(-bm25_scores)
                    d_ranks = {int(i): r + 1 for r, i in enumerate(d_order)}
                    b_ranks = {int(i): r + 1 for r, i in enumerate(b_order)}

                    scored = []
                    for i, p in enumerate(rag_engine.products_cache):
                        s = cfg["alpha"] * float(dense_scores[i]) + cfg["beta"] * float(bm25_scores[i])
                        if cfg["use_rrf"]:
                            s += ((1.0 / (20.0 + d_ranks[i])) + (1.0 / (20.0 + b_ranks[i]))) * 5.0
                        scored.append((s, p["product_id"]))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    top_ids = [pid for _, pid in scored[:5]]

                hits = [1 if pid in expected_set else 0 for pid in top_ids]
                recall_sum += sum(hits) / max(1, len(expected_set))
                for rank_idx, h in enumerate(hits, start=1):
                    if h:
                        mrr_sum += 1.0 / rank_idx
                        break
                dcg = sum(rel / math.log2(idx + 1) for idx, rel in enumerate(hits, start=1))
                idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, min(len(expected_set), 5) + 1))
                ndcg_sum += (dcg / idcg) if idcg > 0 else 0.0

            n = len(sample_qs)
            ablation_results.append(
                {
                    "configuration": cfg["name"],
                    "alpha_dense": cfg["alpha"],
                    "beta_bm25": cfg["beta"],
                    "rrf_enabled": cfg["use_rrf"],
                    "reranker_enabled": cfg["use_reranker"],
                    "mrr": round((mrr_sum / n) * 100.0, 2),
                    "recall_at_5": round((recall_sum / n) * 100.0, 2),
                    "ndcg_at_5": round((ndcg_sum / n) * 100.0, 2),
                }
            )

        return ablation_results

# Bootstrap Confidence Intervals
# This function is used to compute the non-parametric 95% bootstrap confidence intervals and standard errors for ShopMind's RAG evaluation metrics.

    @staticmethod
    def compute_bootstrap_confidence_intervals(db: Session, n_bootstraps: int = 400) -> Dict[str, Any]:
        """Computes non-parametric 95% Bootstrap Confidence Intervals and Standard Errors over the latest EvaluationRun."""
        latest_run = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).first()
        if not latest_run or not latest_run.results:
            return {"run_id": None, "metrics": {}}

        rng = np.random.default_rng(seed=42)
        results = latest_run.results
        n = len(results)

        metric_arrays = {
            "precision_at_k": np.array([r.precision_at_k for r in results], dtype=np.float64),
            "recall_at_k": np.array([r.recall_at_k for r in results], dtype=np.float64),
            "mrr": np.array([r.mrr for r in results], dtype=np.float64),
            "ndcg_at_k": np.array([r.ndcg_at_k for r in results], dtype=np.float64),
            "faithfulness": np.array([r.faithfulness for r in results], dtype=np.float64),
            "answer_relevancy": np.array([r.answer_relevancy for r in results], dtype=np.float64),
            "response_correctness": np.array([r.response_correctness for r in results], dtype=np.float64),
        }

        ci_report: Dict[str, Any] = {}
        for m_name, arr in metric_arrays.items():
            boot_means = np.zeros(n_bootstraps, dtype=np.float64)
            for b in range(n_bootstraps):
                sample_idx = rng.integers(0, n, size=n)
                boot_means[b] = np.mean(arr[sample_idx])
            ci_low, ci_high = np.percentile(boot_means, [2.5, 97.5])
            std_err = float(np.std(boot_means))
            ci_report[m_name] = {
                "mean": round(float(np.mean(arr)), 4),
                "ci_95_lower": round(float(ci_low), 4),
                "ci_95_upper": round(float(ci_high), 4),
                "std_error": round(std_err, 4),
            }

        return {
            "run_id": latest_run.run_id,
            "sample_size_n": n,
            "n_bootstraps": n_bootstraps,
            "confidence_level": "95% Non-Parametric Percentile Bootstrap",
            "metrics": ci_report,
        }

# 