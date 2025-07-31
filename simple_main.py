import os
import requests
import base64
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

# 通常のWordPressサイト（自己ホスト型）用の設定
WP_URL = os.getenv('WP_URL', 'https://open-blogging.com/wp-json/wp/v2/posts')
USERNAME = os.getenv('WP_USERNAME', 'nakaaa')
APPLICATION_PASSWORD = os.getenv('WP_APPLICATION_PASSWORD', 't9eu BcBA xGB9 jtpI ITJf bd9t')

def create_post_with_basic_auth(title, content, status="publish"):
    """Basic認証を使用してWordPressに投稿を作成"""
    payload = {
        "title": title,
        "content": content,
        "status": status  # "publish" または "draft"
    }
    
    # Basic認証のヘッダーを作成
    credentials = f"{USERNAME}:{APPLICATION_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }
    
    # デバッグ情報を表示
    print(f"URL: {WP_URL}")
    print(f"ユーザー名: {USERNAME}")
    print(f"アプリケーションパスワード: {APPLICATION_PASSWORD}")
    print(f"Basic認証ヘッダー: Basic {encoded_credentials[:20]}...")
    print(f"ペイロード: {payload}")
    
    try:
        response = requests.post(
            WP_URL,
            json=payload,
            headers=headers
        )
        
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンスヘッダー: {dict(response.headers)}")
        print(f"レスポンステキスト: {response.text}")
        
        if response.status_code == 201:
            print("投稿が成功しました！")
            try:
                post_data = response.json()
                print(f"投稿ID: {post_data.get('id')}")
                print(f"投稿URL: {post_data.get('link')}")
                return post_data
            except:
                print("レスポンスの解析に失敗しました。")
        elif response.status_code == 401:
            print("認証エラー: ユーザー名またはアプリケーションパスワードが間違っています")
            print("確認事項:")
            print("1. ユーザー名が正しいか確認してください")
            print("2. アプリケーションパスワードが正しく作成されているか確認してください")
            print("3. アプリケーションパスワードに余分なスペースがないか確認してください")
        elif response.status_code == 403:
            print("権限エラー: 投稿する権限がありません")
        elif response.status_code == 404:
            print("エンドポイントが見つかりません: URLを確認してください")
        else:
            print(f"エラーが発生しました: {response.status_code}")
            print(f"レスポンス: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"リクエストエラー: {e}")
    except Exception as e:
        print(f"予期しないエラー: {e}")
    
    return None

def create_post_with_requests_auth(title, content, status="publish"):
    """requestsのauthパラメータを使用してWordPressに投稿を作成"""
    payload = {
        "title": title,
        "content": content,
        "status": status  # "publish" または "draft"
    }
    
    # デバッグ情報を表示
    print(f"URL: {WP_URL}")
    print(f"ユーザー名: {USERNAME}")
    print(f"アプリケーションパスワード: {APPLICATION_PASSWORD}")
    print(f"ペイロード: {payload}")
    
    try:
        response = requests.post(
            WP_URL,
            json=payload,
            auth=(USERNAME, APPLICATION_PASSWORD),
            headers={"Content-Type": "application/json"}
        )
        
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンスヘッダー: {dict(response.headers)}")
        print(f"レスポンステキスト: {response.text}")
        
        if response.status_code == 201:
            print("投稿が成功しました！")
            try:
                post_data = response.json()
                print(f"投稿ID: {post_data.get('id')}")
                print(f"投稿URL: {post_data.get('link')}")
                return post_data
            except:
                print("レスポンスの解析に失敗しました。")
        elif response.status_code == 401:
            print("認証エラー: ユーザー名またはアプリケーションパスワードが間違っています")
        elif response.status_code == 403:
            print("権限エラー: 投稿する権限がありません")
        elif response.status_code == 404:
            print("エンドポイントが見つかりません: URLを確認してください")
        else:
            print(f"エラーが発生しました: {response.status_code}")
            print(f"レスポンス: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"リクエストエラー: {e}")
    except Exception as e:
        print(f"予期しないエラー: {e}")
    
    return None

def test_connection():
    """WordPressサイトへの接続をテスト"""
    print("WordPressサイトへの接続をテストしています...")
    
    try:
        response = requests.get(WP_URL.replace("/posts", ""))
        print(f"ステータスコード: {response.status_code}")
        if response.status_code == 200:
            print("WordPress REST APIに接続できました！")
        else:
            print("WordPress REST APIに接続できませんでした。")
    except Exception as e:
        print(f"接続エラー: {e}")

def main():
    """メイン関数"""
    print("WordPress投稿ツール")
    print("=" * 50)
    
    # 接続テスト
    test_connection()
    print()
    
    # サンプル投稿
    title = "テスト投稿"
    content = """
    <h2>これはテスト投稿です</h2>
    <p>Pythonスクリプトから自動投稿された記事です。</p>
    <p>投稿日時: {}</p>
    """.format(datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"))
    
    print("投稿を作成しています...")
    result = create_post_with_requests_auth(title, content, "draft")
    
    if result:
        print("投稿が正常に作成されました！")
    else:
        print("投稿の作成に失敗しました。")

if __name__ == "__main__":
    from datetime import datetime
    main() 