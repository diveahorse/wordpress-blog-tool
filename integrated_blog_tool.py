import os
import requests
import base64
import sys
from datetime import datetime
from dotenv import load_dotenv
from perplexity_client import PerplexityClient, create_blog_article

# .envファイルから環境変数を読み込み
load_dotenv()

class IntegratedBlogTool:
    def __init__(self):
        """統合ブログツールを初期化"""
        # Perplexity API設定
        self.perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
        if not self.perplexity_api_key:
            raise ValueError("PERPLEXITY_API_KEYが設定されていません。.envファイルを確認してください。")
        
        # WordPress設定
        self.wp_url = os.getenv('WP_URL', 'https://open-blogging.com/wp-json/wp/v2/posts')
        self.wp_username = os.getenv('WP_USERNAME', 'nakaaa')
        self.wp_password = os.getenv('WP_APPLICATION_PASSWORD', 't9eu BcBA xGB9 jtpI ITJf bd9t')
        
        # Perplexityクライアントを初期化
        self.perplexity_client = PerplexityClient()
    
    def generate_and_post_article(self, theme, status="draft", prompt_template_file="prompt_template.txt", max_tokens=4096):
        """
        記事を生成してWordPressに投稿
        
        Args:
            theme (str): 記事のテーマ
            status (str): 投稿ステータス ("draft" または "publish")
            prompt_template_file (str): プロンプトテンプレートファイルのパス
            max_tokens (int): 最大トークン数（デフォルト: 4096）
        
        Returns:
            dict: 投稿結果
        """
        print(f"テーマ '{theme}' で記事を生成中...")
        print(f"使用テンプレート: {prompt_template_file}")
        print(f"最大トークン数: {max_tokens}")
        
        try:
            # 記事を生成
            article = create_blog_article(theme, self.perplexity_client, prompt_template_file, max_tokens)
            
            if not article:
                print("記事の生成に失敗しました。")
                return None
            
            # タイトルとコンテンツを抽出
            lines = article.split('\n')
            title = ""
            content = ""
            in_content = False
            
            for line in lines:
                if line.startswith('# '):
                    title = line[2:].strip()
                elif line.startswith('## ') or line.startswith('### ') or line.startswith('- ') or line.startswith('1. '):
                    in_content = True
                    content += line + '\n'
                elif in_content and line.strip():
                    content += line + '\n'
            
            if not title:
                title = f"{theme}について"
            
            # HTML形式に変換
            html_content = self._convert_to_html(content)
            
            print(f"生成されたタイトル: {title}")
            print("WordPressに投稿中...")
            
            # WordPressに投稿
            result = self._post_to_wordpress(title, html_content, status)
            
            if result:
                print("記事の生成と投稿が完了しました！")
                return {
                    'title': title,
                    'content': html_content,
                    'post_id': result.get('id'),
                    'post_url': result.get('link'),
                    'status': status
                }
            else:
                print("WordPressへの投稿に失敗しました。")
                return None
                
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            return None
    
    def _convert_to_html(self, markdown_content):
        """Markdown形式のコンテンツをHTMLに変換"""
        html = ""
        lines = markdown_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            elif line.startswith('## '):
                html += f"<h2>{line[3:]}</h2>\n"
            elif line.startswith('### '):
                html += f"<h3>{line[4:]}</h3>\n"
            elif line.startswith('- '):
                html += f"<li>{line[2:]}</li>\n"
            elif line.startswith('1. '):
                html += f"<li>{line[3:]}</li>\n"
            else:
                html += f"<p>{line}</p>\n"
        
        return html
    
    def _post_to_wordpress(self, title, content, status="draft"):
        """WordPressに投稿"""
        payload = {
            "title": title,
            "content": content,
            "status": status
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.wp_url,
                json=payload,
                auth=(self.wp_username, self.wp_password),
                headers=headers
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                print(f"投稿エラー: {response.status_code}")
                print(f"レスポンス: {response.text}")
                return None
                
        except Exception as e:
            print(f"投稿エラー: {e}")
            return None
    
    def test_connections(self):
        """Perplexity APIとWordPressの接続をテスト"""
        print("接続テストを実行中...")
        
        # Perplexity APIテスト
        print("1. Perplexity API接続テスト...")
        try:
            test_response = self.perplexity_client.chat_completion([
                {"role": "user", "content": "こんにちは"}
            ])
            if test_response:
                print("✓ Perplexity API接続成功")
            else:
                print("✗ Perplexity API接続失敗")
        except Exception as e:
            print(f"✗ Perplexity API接続エラー: {e}")
        
        # WordPress接続テスト
        print("2. WordPress接続テスト...")
        try:
            response = requests.get(self.wp_url.replace("/posts", ""))
            if response.status_code == 200:
                print("✓ WordPress REST API接続成功")
            else:
                print(f"✗ WordPress接続失敗: {response.status_code}")
        except Exception as e:
            print(f"✗ WordPress接続エラー: {e}")

def main():
    """メイン関数"""
    print("WordPressブログ管理ツール")
    print("=" * 50)
    
    try:
        # コマンドライン引数をチェック
        if len(sys.argv) < 2:
            print("使用方法: python integrated_blog_tool.py <テーマ> [プロンプトテンプレートファイル] [投稿ステータス] [最大トークン数]")
            print("例: python integrated_blog_tool.py '健康な食事の作り方'")
            print("例: python integrated_blog_tool.py '効率的な時間管理術' custom_prompt.txt")
            print("例: python integrated_blog_tool.py 'AI技術の最新動向' prompt_template.txt publish")
            print("例: python integrated_blog_tool.py '最新技術トレンド' prompt_template.txt draft 8192")
            return
        
        # テーマを取得
        theme = sys.argv[1]
        
        # プロンプトテンプレートファイルを取得（オプション）
        prompt_template_file = sys.argv[2] if len(sys.argv) > 2 else "prompt_template.txt"
        
        # 投稿ステータスを取得（オプション）
        status = sys.argv[3] if len(sys.argv) > 3 else "draft"
        
        # 最大トークン数を取得（オプション）
        max_tokens = int(sys.argv[4]) if len(sys.argv) > 4 else 4096
        
        # ツールを初期化
        tool = IntegratedBlogTool()
        
        # 接続テスト
        tool.test_connections()
        print()
        
        if not theme.strip():
            print("テーマが入力されていません。")
            return
        
        # 記事を生成して投稿
        result = tool.generate_and_post_article(theme, status, prompt_template_file, max_tokens)
        
        if result:
            print("\n" + "=" * 50)
            print("投稿完了！")
            print(f"タイトル: {result['title']}")
            print(f"投稿ID: {result['post_id']}")
            print(f"投稿URL: {result['post_url']}")
            print(f"ステータス: {result['status']}")
        else:
            print("投稿に失敗しました。")
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main() 