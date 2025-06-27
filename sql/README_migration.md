# Database Migration Guide - Phase 4

このガイドではSupabaseデータベースのスキーマ修正を実行する手順を説明します。

## 問題の概要

ニュースレター生成時に以下のエラーが発生していました：

```
Could not find the 'articles_count' column of 'processed_content'
Could not find the 'data' column of 'processing_logs'
```

これは、コードが期待するデータベーススキーマと実際のSupabaseデータベースの構造が一致していないために発生していました。

## 解決策

### 1. データベーススキーマの修正

以下のSQLファイルを順次実行します：

#### Step 1: 基本テーブル作成
```bash
# Supabaseダッシュボードのスキーマ管理から実行、または
# psql クライアントを使用
psql <your_supabase_connection_string> -f sql/phase2_tables.sql
```

#### Step 2: Phase 4 マイグレーション
```bash
psql <your_supabase_connection_string> -f sql/migration_phase4.sql
```

### 2. Supabaseダッシュボードから実行する場合

1. Supabaseプロジェクトダッシュボードにログイン
2. 「SQL Editor」セクションに移動
3. `sql/migration_phase4.sql`の内容をコピー＆ペースト
4. 「Run」を実行

## マイグレーション内容

### 新規作成されるテーブル

#### processed_content
```sql
CREATE TABLE processed_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processing_date DATE NOT NULL,
    edition VARCHAR NOT NULL,
    content_type VARCHAR NOT NULL,
    title TEXT NOT NULL,
    lead_paragraph TEXT,
    articles_count INTEGER NOT NULL DEFAULT 0,  -- ✅ 追加
    multi_source_topics INTEGER DEFAULT 0,      -- ✅ 追加
    content_md TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',                 -- ✅ 追加
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(processing_date, edition, content_type)
);
```

#### processing_logs
```sql
CREATE TABLE processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processing_date DATE NOT NULL,
    edition VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    articles_processed INTEGER DEFAULT 0,
    articles_failed INTEGER DEFAULT 0,
    llm_calls INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    processing_time_seconds FLOAT,
    data JSONB DEFAULT '{}',                     -- ✅ 追加
    error_details TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 新規作成されるビュー

#### newsletter_processing_summary
```sql
-- ニュースレター処理の概要を表示
SELECT processing_date, edition, title, articles_count, status
FROM newsletter_processing_summary 
ORDER BY processing_date DESC;
```

#### processing_quality_metrics
```sql
-- 処理品質のメトリクスを表示
SELECT processing_date, success_rate, processing_time_seconds 
FROM processing_quality_metrics 
ORDER BY processing_date DESC;
```

## 実行後の確認

### 1. テーブル存在確認
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('processed_content', 'processing_logs');
```

### 2. カラム存在確認
```sql
-- processed_content テーブルのカラム確認
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'processed_content'
AND column_name IN ('articles_count', 'multi_source_topics', 'metadata');

-- processing_logs テーブルのカラム確認
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'processing_logs'
AND column_name = 'data';
```

### 3. アプリケーションテスト
```bash
# ニュースレター生成テスト
python3 main.py --max-items 5 --edition daily

# ログでエラーがないことを確認
tail -f logs/newsletter_$(date +%Y-%m-%d).json
```

## トラブルシューティング

### エラー: "relation already exists"
既存のテーブルが存在する場合、マイグレーションスクリプトは安全に実行されます。
`IF NOT EXISTS`句により重複作成を回避します。

### エラー: "permission denied"
Supabaseの`service_role`キーを使用していることを確認してください。
環境変数`SUPABASE_KEY`が正しく設定されているか確認してください。

### エラー: "column already exists"
既存のカラムが存在する場合もスクリプトは安全に実行されます。
情報メッセージが表示されるだけで、エラーにはなりません。

## マイグレーション完了後の期待結果

1. ✅ Supabaseへの保存エラーが解消
2. ✅ 処理ログが正常にデータベースに保存
3. ✅ ニュースレターメタデータが適切に記録
4. ✅ 品質メトリクスの監視が可能

## メンテナンス機能

### 古いログのクリーンアップ
```sql
-- 30日以上古いログを削除
SELECT cleanup_old_processing_logs(30);

-- 7日以上古いログを削除
SELECT cleanup_old_processing_logs(7);
```

これでSupabaseデータベースの問題が完全に解決され、ニュースレター生成システムが安定して動作するようになります。