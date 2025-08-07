from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import os
import json
from datetime import datetime
from integrated_blog_tool import IntegratedBlogTool
from perplexity_client import PerplexityClient
import threading
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)

# グローバル変数で生成状態を管理
generation_status = {
    'is_generating': False,
    'progress': 0,
    'current_step': '',
    'result': None,
    'error': None
}

# 利用可能なプロンプトテンプレート
PROMPT_TEMPLATES = {
    'default': {
        'name': '標準テンプレート',
        'file': 'prompt_template.txt',
        'description': '一般的なブログ記事用のテンプレート'
    },
    'anime': {
        'name': 'アニメランキング用',
        'file': 'anime_prompt.txt',
        'description': 'アニメランキング記事専用のテンプレート'
    },
    'custom': {
        'name': 'カスタムテンプレート',
        'file': 'custom_prompt.txt',
        'description': '詳細なガイドライン付きのカスタムテンプレート'
    }
}

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html', prompt_templates=PROMPT_TEMPLATES)

@app.route('/generate', methods=['POST'])
def generate_article():
    """記事生成API"""
    global generation_status
    
    if generation_status['is_generating']:
        return jsonify({'error': '既に記事生成中です。完了までお待ちください。'})
    
    try:
        data = request.get_json()
        theme = data.get('theme', '').strip()
        prompt_type = data.get('prompt_type', 'default')
        status = data.get('status', 'draft')
        max_tokens = int(data.get('max_tokens', 4096))
        
        if not theme:
            return jsonify({'error': 'テーマを入力してください。'})
        
        # 生成状態をリセット
        generation_status.update({
            'is_generating': True,
            'progress': 0,
            'current_step': '初期化中...',
            'result': None,
            'error': None
        })
        
        # バックグラウンドで記事生成を実行
        thread = threading.Thread(
            target=generate_article_background,
            args=(theme, prompt_type, status, max_tokens)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': '記事生成を開始しました。'})
        
    except Exception as e:
        generation_status['error'] = str(e)
        generation_status['is_generating'] = False
        return jsonify({'error': f'エラーが発生しました: {str(e)}'})

def generate_article_background(theme, prompt_type, status, max_tokens):
    """バックグラウンドで記事生成を実行"""
    global generation_status
    
    try:
        # プロンプトテンプレートファイルを取得
        prompt_template_file = PROMPT_TEMPLATES[prompt_type]['file']
        
        generation_status['current_step'] = 'Perplexity APIに接続中...'
        generation_status['progress'] = 10
        
        # ツールを初期化
        tool = IntegratedBlogTool()
        
        generation_status['current_step'] = '記事を生成中...'
        generation_status['progress'] = 30
        
        # 記事を生成
        result = tool.generate_and_post_article(
            theme=theme,
            status=status,
            prompt_template_file=prompt_template_file,
            max_tokens=max_tokens
        )
        
        generation_status['progress'] = 90
        generation_status['current_step'] = '完了処理中...'
        
        if result:
            generation_status['result'] = result
            generation_status['progress'] = 100
            generation_status['current_step'] = '完了！'
        else:
            generation_status['error'] = '記事の生成に失敗しました。'
            
    except Exception as e:
        generation_status['error'] = str(e)
    finally:
        generation_status['is_generating'] = False

@app.route('/status')
def get_status():
    """生成状態を取得"""
    return jsonify(generation_status)

@app.route('/test-connections')
def test_connections():
    """接続テスト"""
    try:
        tool = IntegratedBlogTool()
        tool.test_connections()
        return jsonify({'message': '接続テストが完了しました。'})
    except Exception as e:
        return jsonify({'error': f'接続テストでエラーが発生しました: {str(e)}'})

@app.route('/history')
def history():
    """生成履歴ページ"""
    # 生成された記事ファイルを取得
    history_files = []
    for filename in os.listdir('.'):
        if filename.startswith('blog_article_') and filename.endswith('.txt'):
            file_path = filename
            file_size = os.path.getsize(filename)
            file_time = datetime.fromtimestamp(os.path.getmtime(filename))
            
            # ファイル名からテーマを抽出
            theme = filename.replace('blog_article_', '').replace('.txt', '')
            
            history_files.append({
                'filename': filename,
                'theme': theme,
                'size': file_size,
                'created_at': file_time.strftime('%Y-%m-%d %H:%M:%S'),
                'file_path': file_path
            })
    
    # 作成日時でソート（新しい順）
    history_files.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('history.html', history_files=history_files)

@app.route('/view/<filename>')
def view_article(filename):
    """記事ファイルを表示"""
    try:
        file_path = os.path.join('.', filename)
        if not os.path.exists(file_path):
            flash('ファイルが見つかりません。', 'error')
            return redirect(url_for('history'))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return render_template('view_article.html', 
                             filename=filename, 
                             content=content,
                             theme=filename.replace('blog_article_', '').replace('.txt', ''))
    except Exception as e:
        flash(f'ファイルの読み込みでエラーが発生しました: {str(e)}', 'error')
        return redirect(url_for('history'))

@app.route('/delete/<filename>')
def delete_article(filename):
    """記事ファイルを削除"""
    try:
        file_path = os.path.join('.', filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('ファイルを削除しました。', 'success')
        else:
            flash('ファイルが見つかりません。', 'error')
    except Exception as e:
        flash(f'ファイルの削除でエラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('history'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
