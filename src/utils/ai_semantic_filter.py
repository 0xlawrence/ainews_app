"""
Semantic AI Content Filter using embeddings for improved relevance detection.

This module provides enhanced AI content filtering that goes beyond keyword matching
to use semantic similarity analysis for more accurate AI relevance scoring.
"""

import asyncio
import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from src.models.schemas import RawArticle, FilteredArticle
from src.utils.logger import setup_logging

try:
    from src.utils.embedding_manager import EmbeddingManager
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False
    EmbeddingManager = None

logger = setup_logging()


@dataclass
class SemanticScore:
    """Semantic analysis results for an article."""
    ai_similarity: float
    non_ai_similarity: float
    final_score: float
    reason: str


class AISemanticFilter:
    """Enhanced AI content filter using semantic analysis."""
    
    def __init__(self):
        self.embedding_manager = None
        self.ai_reference_embeddings = None
        self.non_ai_reference_embeddings = None
        self.initialized = False
        
        # AI関連の理想的な記事例（多様なAI分野をカバー）
        self.ai_examples = [
            "OpenAI GPT-4o 大規模言語モデル 推論能力向上 API提供開始 自然言語処理",
            "Google Gemini Pro マルチモーダルAI 画像理解 動画解析 機械学習",
            "Anthropic Claude 3 constitutional AI 安全性 長文処理 対話システム",
            "Meta LLaMA 3.5 オープンソース 商用利用 コミュニティ開発 transformer",
            "Microsoft Copilot AI開発支援 コード生成 自動化 プログラミング",
            "AI研究 transformer architecture attention mechanism ニューラルネットワーク",
            "機械学習 深層学習 ニューラルネットワーク 自然言語処理 computer vision",
            "AIエージェント 自動化 ビジネス活用 生産性向上 企業導入",
            "生成AI 創作支援 画像生成 音声合成 multimodal AI",
            "AGI 人工汎用知能 研究開発 技術革新 社会実装",
            "AI倫理 安全性 責任あるAI バイアス対策 透明性",
            "大規模言語モデル LLM fine-tuning RLHF 学習手法"
        ]
        
        # 除外したい非AI記事例（強化版）
        self.non_ai_examples = [
            "電気自動車 EV バッテリー リサイクル 充電インフラ 自動車産業 電池再利用 エネルギー貯蔵",
            "iPhone 設定 Tailscale SSH Termius 接続方法 スマートフォン設定 モバイル設定",
            "仮想通貨 ビットコイン イーサリアム DeFi NFT ブロックチェーン取引 暗号通貨",
            "不動産投資 住宅ローン 金利 資産運用 投資信託 金融商品",
            "スマートフォン アプリ開発 iOS Android モバイル開発 アプリストア",
            "ネットワーク設定 VPN セキュリティ インフラ システム管理 サーバー設定",
            "Web3 メタバース ゲーム エンタメ 仮想現実 ゲーム開発",
            "金融 銀行 投資 株式 為替 経済指標 資産管理",
            "ハードウェア CPU GPU メモリ ストレージ 半導体製造 コンピューター部品",
            "オペレーティングシステム Windows macOS Linux システム設定 OS管理",
            "電力供給 データセンター インフラ 電力安定化 エネルギー効率 電力管理",
            "起業家支援 スタートアップ投資 ベンチャーキャピタル 事業計画",
            "ソフトウェア開発 プログラミング言語 開発環境 IDE設定"
        ]
        
    async def initialize(self):
        """セマンティックフィルターの初期化"""
        if not HAS_EMBEDDINGS:
            logger.warning("Embedding manager not available, semantic filtering disabled")
            return False
            
        try:
            self.embedding_manager = EmbeddingManager()
            
            # AI関連記事の参照embeddings生成
            logger.info("Generating AI reference embeddings...")
            self.ai_reference_embeddings = []
            for example in self.ai_examples:
                embedding = await self.embedding_manager.get_embedding(example)
                if embedding is not None:
                    self.ai_reference_embeddings.append(embedding)
            
            # 非AI記事の参照embeddings生成
            logger.info("Generating non-AI reference embeddings...")
            self.non_ai_reference_embeddings = []
            for example in self.non_ai_examples:
                embedding = await self.embedding_manager.get_embedding(example)
                if embedding is not None:
                    self.non_ai_reference_embeddings.append(embedding)
                    
            if self.ai_reference_embeddings and self.non_ai_reference_embeddings:
                self.initialized = True
                logger.info(
                    f"Semantic filter initialized: "
                    f"{len(self.ai_reference_embeddings)} AI examples, "
                    f"{len(self.non_ai_reference_embeddings)} non-AI examples"
                )
                return True
            else:
                logger.error("Failed to generate reference embeddings")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize semantic filter: {e}")
            return False
    
    async def calculate_semantic_score(self, text: str) -> SemanticScore:
        """セマンティックAIスコアを計算"""
        if not self.initialized:
            return SemanticScore(0.0, 0.0, 0.0, "Semantic filter not initialized")
            
        try:
            # テキストのembedding生成（最初の1000文字）
            embedding = await self.embedding_manager.get_embedding(text[:1000])
            if embedding is None:
                return SemanticScore(0.0, 0.0, 0.0, "Failed to generate embedding")
            
            # AI記事との類似度計算（上位3つの平均）
            ai_similarities = []
            for ref_emb in self.ai_reference_embeddings:
                # コサイン類似度計算
                sim = float(np.dot(embedding, ref_emb) / (np.linalg.norm(embedding) * np.linalg.norm(ref_emb)))
                ai_similarities.append(sim)
            ai_similarities.sort(reverse=True)
            avg_ai_sim = np.mean(ai_similarities[:3])
            
            # 非AI記事との類似度計算（上位3つの平均）  
            non_ai_similarities = []
            for ref_emb in self.non_ai_reference_embeddings:
                sim = float(np.dot(embedding, ref_emb) / (np.linalg.norm(embedding) * np.linalg.norm(ref_emb)))
                non_ai_similarities.append(sim)
            non_ai_similarities.sort(reverse=True)
            avg_non_ai_sim = np.mean(non_ai_similarities[:3])
            
            # スコア計算：AI類似度 - 非AI類似度のペナルティ（緩和版）
            # 非AI類似度が高い場合のペナルティを緩和
            non_ai_penalty_multiplier = 0.6 if avg_non_ai_sim > 0.7 else 0.4
            semantic_score = avg_ai_sim - (avg_non_ai_sim * non_ai_penalty_multiplier)
            semantic_score = max(0.0, min(1.0, semantic_score))  # 0-1に正規化
            
            # 理由の生成
            if semantic_score > 0.6:
                reason = f"High AI relevance (AI:{avg_ai_sim:.2f}, Non-AI:{avg_non_ai_sim:.2f})"
            elif semantic_score > 0.3:
                reason = f"Moderate AI relevance (AI:{avg_ai_sim:.2f}, Non-AI:{avg_non_ai_sim:.2f})"
            else:
                reason = f"Low AI relevance (AI:{avg_ai_sim:.2f}, Non-AI:{avg_non_ai_sim:.2f})"
            
            return SemanticScore(
                ai_similarity=float(avg_ai_sim),
                non_ai_similarity=float(avg_non_ai_sim), 
                final_score=float(semantic_score),
                reason=reason
            )
            
        except Exception as e:
            logger.warning(f"Semantic scoring failed: {e}")
            return SemanticScore(0.0, 0.0, 0.0, f"Error: {str(e)}")
    
    def _calculate_keyword_relevance(self, article: RawArticle) -> Tuple[float, List[str], str]:
        """従来のキーワードベース関連度計算"""
        
        # 高価値AIキーワード（重み付け）
        high_value_keywords = {
            # LLM関連
            'gpt': 1.0, 'chatgpt': 1.0, 'claude': 1.0, 'gemini': 1.0, 'llama': 1.0,
            'large language model': 1.0, 'llm': 1.0, 'transformer': 0.9,
            
            # 企業・組織
            'openai': 1.0, 'anthropic': 1.0, 'deepmind': 0.9, 'google ai': 0.9,
            'meta ai': 0.9, 'microsoft ai': 0.8,
            
            # 技術用語
            'artificial intelligence': 0.9, 'machine learning': 0.8, 'deep learning': 0.8,
            'neural network': 0.7, 'generative ai': 0.9, 'multimodal': 0.8,
            
            # 応用分野
            'ai agent': 0.9, 'automation': 0.6, 'ai assistant': 0.8,
            'computer vision': 0.7, 'natural language processing': 0.8,
        }
        
        # 除外キーワード（非AI分野）- 強化版
        exclusion_keywords = {
            # EV/バッテリー関連
            'electric vehicle', 'ev battery', 'battery recycling', 'energy storage business',
            'charging infrastructure', 'automotive industry', 'redwood materials',
            
            # iPhone/モバイル設定関連
            'iphone setup', 'smartphone config', 'tailscale setup', 'termius setup',
            'mobile configuration', 'ssh connection', 'ios configuration',
            
            # 仮想通貨/金融関連
            'real estate', 'cryptocurrency', 'bitcoin', 'ethereum', 'nft',
            'defi', 'blockchain trading', 'investment fund', 'financial product',
            
            # Web3/ゲーム/エンタメ関連
            'web3', 'metaverse game', 'social media', 'entertainment',
            'virtual reality game', 'gaming development',
            
            # インフラ/システム管理関連
            'network configuration', 'vpn setup', 'server management',
            'system administration', 'infrastructure management',
            
            # ハードウェア関連
            'computer hardware', 'cpu specs', 'gpu benchmarks', 'memory upgrade',
            'storage solutions', 'semiconductor manufacturing'
        }
        
        # テキスト結合と正規化
        full_text = f"{article.title} {article.content}".lower()
        
        # 除外チェック（強化版）
        for exclusion in exclusion_keywords:
            if exclusion in full_text:
                return 0.05, [], f"Excluded: contains '{exclusion}'"  # さらに低いスコア
        
        # 特定の非AI記事パターンの追加チェック
        non_ai_patterns = [
            r'バッテリー.*リサイクル',
            r'電気自動車.*充電',
            r'iphone.*設定.*方法',
            r'スマートフォン.*接続',
            r'投資.*不動産',
            r'仮想通貨.*取引'
        ]
        
        for pattern in non_ai_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                return 0.03, [], f"Excluded: matches non-AI pattern '{pattern}'"  # 極めて低いスコア
        
        # キーワードマッチング
        matched_keywords = []
        total_score = 0.0
        
        for keyword, weight in high_value_keywords.items():
            if keyword in full_text:
                matched_keywords.append(keyword)
                total_score += weight
        
        # 正規化（最大3つのキーワードでスコア1.0）
        normalized_score = min(total_score / 3.0, 1.0)
        
        reason = f"Keywords: {', '.join(matched_keywords[:3])}" if matched_keywords else "No AI keywords"
        
        return normalized_score, matched_keywords, reason
    
    async def filter_articles_with_semantic(
        self, 
        articles: List[RawArticle], 
        base_threshold: float = 0.20,  # PRD準拠：7-10記事確保のため大幅緩和
        min_threshold: float = 0.10   # 最低閾値も大幅緩和
    ) -> List[FilteredArticle]:
        """セマンティック分析を含む高度なフィルタリング"""
        
        # セマンティックフィルター初期化（初回のみ）
        if not self.initialized:
            await self.initialize()
        
        enhanced_scores = []
        
        for article in articles:
            try:
                # 既存のキーワードスコア
                keyword_score, keywords, keyword_reason = self._calculate_keyword_relevance(article)
                
                # セマンティックスコア
                article_text = f"{article.title} {article.content[:800]}"
                semantic_result = await self.calculate_semantic_score(article_text)
                
                # 統合スコア計算（セマンティックの重みを下げる）
                if self.initialized and semantic_result.final_score > 0:
                    # セマンティック分析が利用可能な場合：キーワード70% + セマンティック30%
                    final_score = keyword_score * 0.7 + semantic_result.final_score * 0.3
                    reason = f"{keyword_reason} | {semantic_result.reason}"
                else:
                    # セマンティック分析が利用できない場合：キーワードのみ
                    final_score = keyword_score
                    reason = keyword_reason
                
                # スコア調整
                final_score = max(0.0, min(1.0, final_score))
                
                enhanced_scores.append((
                    article, final_score, keywords, reason, semantic_result
                ))
                
            except Exception as e:
                logger.warning(f"Error processing article {article.title[:50]}: {e}")
                # エラーの場合は低スコアで継続
                enhanced_scores.append((
                    article, 0.2, [], f"Processing error: {str(e)}", 
                    SemanticScore(0.0, 0.0, 0.0, "Error")
                ))
        
        # スコア順にソート
        enhanced_scores.sort(key=lambda x: x[1], reverse=True)
        
        # フィルタリング：閾値を満たす記事を選択
        filtered_articles = []
        
        for article, score, keywords, reason, semantic_result in enhanced_scores:
            # 基本閾値をクリアするか、PRD要件(7-10記事)確保のため低閾値をクリア
            if score >= base_threshold or (len(filtered_articles) < 15 and score >= min_threshold):
                # セマンティック情報を含むメタデータを作成
                semantic_metadata = {
                    'semantic_score': semantic_result.final_score,
                    'ai_similarity': semantic_result.ai_similarity,
                    'non_ai_similarity': semantic_result.non_ai_similarity,
                    'semantic_reason': semantic_result.reason
                }
                
                # フィルター理由にセマンティック情報を含める
                enhanced_reason = f"{reason} (Semantic: {semantic_result.final_score:.2f})"
                
                filtered_article = FilteredArticle(
                    raw_article=article,
                    ai_relevance_score=score,
                    ai_keywords=keywords,
                    filter_reason=enhanced_reason
                )
                
                filtered_articles.append(filtered_article)
                
                logger.info(
                    f"Accepted article (score: {score:.2f}): {article.title[:60]}..."
                )
            else:
                logger.info(
                    f"Rejected article (score: {score:.2f}): {article.title[:60]}..."
                )
        
        logger.info(
            f"Semantic filtering completed: {len(articles)} → {len(filtered_articles)} articles"
        )
        
        return filtered_articles


# 従来のフィルターとの統合用ファクトリー関数
async def create_enhanced_ai_filter():
    """Enhanced AI filter インスタンスを作成"""
    filter_instance = AISemanticFilter()
    await filter_instance.initialize()
    return filter_instance