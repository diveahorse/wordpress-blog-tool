# WordPressブログ管理ツール

このプロジェクトは、Perplexity APIを使用してSEO最適化されたブログ記事を自動生成し、WordPressに自動投稿するPythonツールです。

## 機能概要

### 1. ブログ記事生成機能
- Perplexity APIを使用した高品質なブログ記事の自動生成
- カスタマイズ可能なプロンプトテンプレート
- SEO最適化されたタイトルとコンテンツ
- 5つのブロック構成の記事
- 自動ファイル保存
- **長い記事対応（最大トークン数調整可能）**

### 2. WordPress投稿機能
- 通常のWordPressサイト（自己ホスト型）への自動投稿
- Basic認証による安全な投稿
- 下書き・公開の選択可能
- 接続テスト機能

## セットアップ

### 1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 2. 仮想環境の使用（推奨）
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate     # Windows
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

#### 基本的な使用方法
```bash
# デフォルトのプロンプトテンプレートを使用（max_tokens: 4096）
python perplexity_client.py "健康な食事の作り方"

# カスタムプロンプトテンプレートを使用
python perplexity_client.py "効率的な時間管理術" custom_prompt.txt

# より長い記事を生成（max_tokens: 8192）
python perplexity_client.py "AI技術の最新動向" prompt_template.txt 8192
```

#### プログラムから使用
```python
from perplexity_client import PerplexityClient, create_blog_article

# クライアントを初期化
client = PerplexityClient()

# デフォルトテンプレートでブログ記事を生成（max_tokens: 4096）
theme = "健康な食事の作り方"
article = create_blog_article(theme, client)

# カスタムテンプレートでブログ記事を生成
article = create_blog_article(theme, client, "custom_prompt.txt")

# より長い記事を生成（max_tokens: 8192）
article = create_blog_article(theme, client, "prompt_template.txt", 8192)
print(article)
```

### WordPress投稿

#### 基本的な使用方法
```bash
# デフォルトテンプレートで下書きとして投稿
python integrated_blog_tool.py "健康な食事の作り方"

# カスタムテンプレートで公開として投稿
python integrated_blog_tool.py "効率的な時間管理術" custom_prompt.txt publish

# より長い記事を生成して投稿
python integrated_blog_tool.py "最新技術トレンド" prompt_template.txt draft 8192
```

#### プログラムから使用
```python
from integrated_blog_tool import IntegratedBlogTool

# ツールを初期化
tool = IntegratedBlogTool()

# 記事を生成してWordPressに投稿
result = tool.generate_and_post_article("健康な食事の作り方", "draft", "prompt_template.txt")

# より長い記事を生成して投稿
result = tool.generate_and_post_article("AI技術の最新動向", "publish", "prompt_template.txt", 8192)
```

### 実行例

1. **ブログ記事生成**:
```bash
python perplexity_client.py "健康な食事の作り方"
```

2. **WordPress投稿**:
```bash
python integrated_blog_tool.py "効率的な時間管理術"
```

3. **統合実行（長い記事）**:
```bash
python integrated_blog_tool.py "AI技術の最新動向" prompt_template.txt publish 8192
```

## プロンプトテンプレート

### デフォルトテンプレート
`prompt_template.txt`ファイルには、ブログ記事生成用のプロンプトテンプレートが含まれています。

### カスタムテンプレートの作成
独自のプロンプトテンプレートを作成する場合：

1. 新しいテキストファイルを作成
2. プロンプトを記述（`{theme}`プレースホルダーを使用）
3. ファイルを引数として指定

例：
```txt
あなたは専門的な技術ライターです。
以下のテーマについて詳細な記事を書いてください：

テーマ: {theme}

要求事項：
- 技術的な詳細を含める
- 実践的な例を提供する
- 最新のトレンドを反映する
```

## 長い記事の生成について

### 文字切れ問題の解決
以前は`max_tokens: 1024`の制限により記事が途中で切れる問題がありましたが、以下の修正により解決しました：

- **デフォルトのmax_tokensを4096に増加**
- **コマンドライン引数でmax_tokensを指定可能**
- **8192トークンまで対応可能**

### 推奨設定
- **短い記事**: 2048-4096トークン
- **標準的な記事**: 4096-8192トークン
- **詳細な記事**: 8192トークン以上

### 使用例
```bash
# 短い記事
python perplexity_client.py "簡単なレシピ" prompt_template.txt 2048

# 標準的な記事
python perplexity_client.py "技術解説" prompt_template.txt 4096

# 詳細な記事
python perplexity_client.py "包括的なガイド" prompt_template.txt 8192
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

### 記事生成関連
- **文字切れ**: `max_tokens`を増やしてください（例：8192）
- **不完全な記事**: より詳細なプロンプトテンプレートを使用してください

### WordPress関連
- **401エラー**: ユーザー名またはアプリケーションパスワードが間違っています
- **403エラー**: 投稿する権限がありません
- **404エラー**: エンドポイントが見つかりません。URLを確認してください

## 注意事項

- Perplexity APIの利用制限と料金体系を確認してください
- 生成された記事は参考として使用し、必要に応じて編集してください
- 大量の投稿は避けてください
- プロンプトテンプレートは適切に管理し、機密情報を含めないでください
- **長い記事を生成する場合は、APIコストが増加する可能性があります**

## ファイル構成

```
wordpress/
├── perplexity_client.py    # Perplexity APIクライアント
├── simple_main.py         # WordPress投稿機能
├── integrated_blog_tool.py # 統合ツール
├── prompt_template.txt    # プロンプトテンプレート
├── requirements.txt       # 依存関係
├── .env                  # 環境変数（要作成）
├── .gitignore           # Git除外設定
└── README.md            # このファイル
```

## 参考リンク

- [Perplexity API ドキュメント](https://docs.perplexity.ai/)
- [API設定](https://www.perplexity.ai/settings/api)
- [WordPress REST API ドキュメント](https://developer.wordpress.org/rest-api/) 