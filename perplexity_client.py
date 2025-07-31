import os
import requests
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

class PerplexityClient:
    def __init__(self):
        """Perplexity APIクライアントを初期化"""
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEYが設定されていません。.envファイルを確認してください。")
        
        self.base_url = "https://api.perplexity.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 公式ドキュメントに基づく利用可能なモデル
        self.available_models = {
            "sonar": "sonar",
            "sonar-reasoning": "sonar-reasoning",
            "sonar-deep-research": "sonar-deep-research"
        }
    
    def chat_completion(self, messages, model="sonar"):
        """
        Perplexity APIを使用してチャット補完を実行
        
        Args:
            messages (list): メッセージのリスト
            model (str): 使用するモデル名（キーまたはフルネーム）
        
        Returns:
            dict: APIレスポンス
        """
        url = f"{self.base_url}/chat/completions"
        
        # モデル名を解決
        actual_model = self.available_models.get(model, model)
        
        payload = {
            "model": actual_model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
            "stream": False
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTPエラー: {e}")
            if response.status_code == 400:
                print("リクエストの形式が正しくありません。APIキーとリクエスト内容を確認してください。")
                print(f"レスポンス内容: {response.text}")
            elif response.status_code == 401:
                print("認証エラー: APIキーが無効です。")
            elif response.status_code == 429:
                print("レート制限エラー: リクエスト数が上限に達しました。")
            return None
        except requests.exceptions.RequestException as e:
            print(f"APIリクエストエラー: {e}")
            return None
    
    def search(self, query):
        """
        検索クエリを実行
        
        Args:
            query (str): 検索クエリ
        
        Returns:
            dict: 検索結果
        """
        url = f"{self.base_url}/search"
        
        payload = {
            "query": query
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"検索HTTPエラー: {e}")
            print(f"レスポンス内容: {response.text}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"検索エラー: {e}")
            return None
    
    def list_models(self):
        """利用可能なモデル一覧を表示"""
        print("利用可能なモデル（公式ドキュメントに基づく）:")
        for key, value in self.available_models.items():
            print(f"  {key}: {value}")

def create_blog_article(theme, client):
    """
    ブログ記事を生成する
    
    Args:
        theme (str): 記事のテーマ
        client (PerplexityClient): Perplexity APIクライアント
    
    Returns:
        str: 生成されたブログ記事
    """
    
    # Webライターとしてのプロンプト
    prompt = f"""あなたはプロのWebライターです。
以下の【テーマ】について【ステップ】に従って
ブログ記事を書いてください。

#テーマ
{theme}

#ステップ
1: テーマにあわせた記事のタイトルを多数考えて、その中から、SEOの観点から、もっともアクセス数が伸び、読者がクリックしたくなると予測される{{タイトル}}を選びます。

2: {{タイトル}}をもとに、5つの記事ブロックに分けて{{アウトライン}}を作成します。

3: {{アウトライン}} を元に、第1ブロックの{{記事文章}}を作成します。

4: {{記事文章}}を、SEOと読みやすさの観点から、修正して{{最終文章}} として出力します。

5: 同様にして、第2ブロック、第3ブロック、第4ブロック、第5ブロックまでの{{最終文章}}を出力します。

6: すべてのブロックの内容を要約して、まとめの文章を作成します。SEOと読みやすさの観点から、それを修正して{{まとめの文章}} として出力します。"""

    messages = [
        {"role": "user", "content": prompt}
    ]
    
    print(f"テーマ「{theme}」についてブログ記事を生成中...")
    
    response = client.chat_completion(messages, model="sonar")
    
    if response:
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        return content
    else:
        return "ブログ記事の生成に失敗しました。"

def main():
    """使用例"""
    try:
        # クライアントを初期化
        client = PerplexityClient()
        
        # 利用可能なモデルを表示
        client.list_models()
        print()
        
        # テーマを入力
        theme = input("ブログ記事のテーマを入力してください: ")
        
        if not theme.strip():
            print("テーマが入力されていません。")
            return
        
        # ブログ記事を生成
        article = create_blog_article(theme, client)
        
        print("\n" + "="*60)
        print("生成されたブログ記事")
        print("="*60)
        print(article)
        
        # ファイルに保存
        filename = f"blog_article_{theme.replace(' ', '_')[:20]}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(article)
        
        print(f"\n記事を {filename} に保存しました。")
            
    except ValueError as e:
        print(f"設定エラー: {e}")
        print("\n.envファイルを作成して、以下のように設定してください:")
        print("PERPLEXITY_API_KEY=your_actual_api_key_here")
        print("\nPerplexity APIキーは以下から取得できます:")
        print("https://www.perplexity.ai/settings/api")
    except Exception as e:
        print(f"予期しないエラー: {e}")

if __name__ == "__main__":
    main() 