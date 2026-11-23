export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'user' | 'admin';
  is_active: boolean;
  created_at: string;
}

export interface Product {
  id?: number;
  product_id: string;
  name: string;
  brand: string;
  category: string;
  description: string;
  price: number;
  discount: number;
  rating: number;
  review_count: number;
  specifications: Record<string, string>;
  features: string[];
  availability: string;
  image_url: string;
  product_url: string;
  product_metadata?: Record<string, any>;
  why_recommended?: string;
  relevance_score?: number;
}

export interface Citation {
  citation_index: number;
  product_id: string;
  name: string;
  brand: string;
  price: number;
  source_url: string;
  dense_score: number;
  bm25_score: number;
  rerank_score: number;
  evidence_snippet: string;
}

export interface ComparisonRow extends Product {
  pros: string[];
  cons: string[];
  value_for_money_score: number;
}

export interface ChatResponseData {
  conversation_id: string;
  answer: string;
  intent: string;
  extracted_constraints: Record<string, any>;
  rewritten_query: string;
  recommended_products: Product[];
  comparison_table?: ComparisonRow[] | null;
  citations: Citation[];
  confidence_score: number;
  grounding_verified: boolean;
  security_status: {
    safe: boolean;
    reason: string;
    risk_category: string;
    severity: string;
  };
  latency_ms: number;
  llm_provider: string;
}

export interface EvaluationQuestionResult {
  question_id: string;
  category: string;
  query: string;
  expected_product_ids: string[];
  retrieved_product_ids: string[];
  expected_answer: string;
  generated_answer: string;
  precision_at_k: number;
  recall_at_k: number;
  mrr: number;
  ndcg_at_k: number;
  hit_rate: number;
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  context_recall: number;
  response_correctness: number;
  hallucination_rate: number;
  latency_ms: number;
  passed: boolean;
  failure_reason?: string | null;
}

export interface EvaluationRunData {
  run_id: string;
  dataset_name: string;
  is_synthetic_benchmark: boolean;
  total_questions: number;
  passed_questions: number;
  failed_questions: number;
  pass_rate: number;
  overall_score: number;
  precision_at_k: number;
  recall_at_k: number;
  mrr: number;
  hit_rate_at_k: number;
  ndcg_at_k: number;
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  context_recall: number;
  response_correctness: number;
  hallucination_rate: number;
  avg_latency_ms: number;
  avg_retrieval_latency_ms: number;
  avg_generation_latency_ms: number;
  total_tokens: number;
  estimated_cost_usd: number;
  retrieval_success_rate: number;
  thresholds: Record<string, number>;
  metric_pass_status: Record<string, boolean>;
  category_breakdown: Record<string, {
    total: number;
    passed: number;
    pass_rate: number;
    precision_at_k: number;
    recall_at_k: number;
    mrr: number;
    faithfulness: number;
    response_correctness: number;
  }>;
  status: string;
  created_at: string;
  question_results?: EvaluationQuestionResult[];
  failed_cases?: EvaluationQuestionResult[];
}
