# WordPressブログ管理ツール

このプロジェクトは、Perplexity APIを使用してSEO最適化されたブログ記事を自動生成し、WordPressに自動投稿するPythonツールです。

## 機能概要

### 1. ブログ記事生成機能
- Perplexity APIを使用した高品質なブログ記事の自動生成
- SEO最適化されたタイトルとコンテンツ
- 5つのブロック構成の記事
- 自動ファイル保存

### 2. WordPress投稿機能
- 通常のWordPressサイト（自己ホスト型）への自動投稿
- Basic認証による安全な投稿
- 下書き・公開の選択可能
- 接続テスト機能

## セットアップ

### 1. 仮想環境の有効化
```bash
source venv/bin/activate
```

### 2. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 3. 環境変数の設定
プロジェクトのルートディレクトリに`.env`ファイルを作成し、以下の内容を追加してください：

```
# Perplexity API設定
PERPLEXITY_API_KEY=your_actual_perplexity_api_key_here

# WordPress設定
WP_URL=https://your-wordpress-site.com/wp-json/wp/v2/posts
WP_USERNAME=your_username
WP_APPLICATION_PASSWORD=your_application_password
```

**重要**: 
- `your_actual_perplexity_api_key_here`を実際のPerplexity APIキーに置き換えてください
- WordPressの設定は実際のサイト情報に変更してください

## 使用方法

### ブログ記事生成

```python
from perplexity_client import PerplexityClient, create_blog_article

# クライアントを初期化
client = PerplexityClient()

# ブログ記事を生成
theme = "健康な食事の作り方"
article = create_blog_article(theme, client)
print(article)
```

### WordPress投稿

```python
from simple_main import create_post_with_requests_auth

# 投稿を作成
title = "記事タイトル"
content = "<h2>記事内容</h2><p>HTML形式で記述</p>"
result = create_post_with_requests_auth(title, content, "draft")
```

### 実行例

1. **ブログ記事生成**:
```bash
python perplexity_client.py
```

2. **WordPress投稿**:
```bash
python simple_main.py
```

3. **統合実行**:
```bash
python integrated_blog_tool.py
```

## WordPress設定

### アプリケーションパスワードの作成

1. WordPress管理画面にログイン
2. ユーザー → プロフィール → アプリケーションパスワード
3. 新しいアプリケーションパスワードを作成
4. 生成されたパスワードを`.env`ファイルに設定

### 権限の確認

- 投稿権限があるユーザーアカウントを使用
- WordPress REST APIが有効になっていることを確認

## ブログ記事生成の特徴

### 生成プロセス
1. **タイトル生成**: SEO最適化された魅力的なタイトルを生成
2. **アウトライン作成**: 5つのブロックに分けた構成を作成
3. **記事執筆**: 各ブロックの詳細な記事を執筆
4. **SEO最適化**: 読みやすさとSEOの観点から修正
5. **まとめ作成**: 全体をまとめた結論を生成

### 生成される内容
- SEO最適化されたタイトル
- 5つのブロック構成の記事
- 読みやすい文章
- まとめの文章
- 自動ファイル保存

## 利用可能なモデル

Perplexity APIの利用可能なモデル：

- **sonar**: Sonar（軽量でコスト効率的な検索モデル）
- **sonar-reasoning**: Sonar Reasoning（高速なリアルタイム推論モデル）
- **sonar-deep-research**: Sonar Deep Research（専門レベルの研究モデル）

## エラーの対処法

### Perplexity API関連
- **401エラー**: APIキーが無効です。.envファイルを確認してください
- **429エラー**: レート制限に達しました。しばらく待ってから再試行してください
- **400エラー**: リクエストの形式が正しくありません

### WordPress関連
- **401エラー**: ユーザー名またはアプリケーションパスワードが間違っています
- **403エラー**: 投稿する権限がありません
- **404エラー**: エンドポイントが見つかりません。URLを確認してください

## 注意事項

- APIキーは必ず.envファイルで管理し、Gitにコミットしないでください
- .envファイルは.gitignoreに追加することを推奨します
- Perplexity APIの利用制限と料金体系を確認してください
- 生成された記事は参考として使用し、必要に応じて編集してください
- 大量の投稿は避けてください

## ファイル構成

```
wordpress/
├── perplexity_client.py    # Perplexity APIクライアント
├── simple_main.py         # WordPress投稿機能
├── integrated_blog_tool.py # 統合ツール（新規作成予定）
├── requirements.txt       # 依存関係
├── .env                  # 環境変数（要作成）
├── .gitignore           # Git除外設定
└── README.md            # このファイル
```

## 参考リンク

- [Perplexity API ドキュメント](https://docs.perplexity.ai/)
- [API設定](https://www.perplexity.ai/settings/api)
- [WordPress REST API ドキュメント](https://developer.wordpress.org/rest-api/) 