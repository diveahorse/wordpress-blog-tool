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

def load_prompt_templates():
    """ローカルファイルからプロンプトテンプレートを動的に読み込み"""
    templates = {}
    
    # プロンプトテンプレートファイルのパターン
    prompt_files = [
        'prompt_template.txt',
        'anime_prompt.txt', 
        'custom_prompt.txt'
    ]
    
    # 追加のプロンプトファイルを検索（prompt_*.txt）
    for filename in os.listdir('.'):
        if filename.startswith('prompt_') and filename.endswith('.txt') and filename not in prompt_files:
            prompt_files.append(filename)
    
    for filename in prompt_files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # ファイル名からテンプレート名を生成
                template_name = filename.replace('prompt_', '').replace('.txt', '')
                if template_name == 'template':
                    template_name = 'default'
                
                # テンプレート名を改善
                display_name = template_name.replace('_', ' ').title()
                if not display_name.endswith('テンプレート'):
                    display_name += 'テンプレート'
                
                # 説明を生成（最初の数行から）
                lines = content.split('\n')
                description = lines[0][:50] + '...' if len(lines[0]) > 50 else lines[0]
                
                templates[template_name] = {
                    'name': display_name,
                    'file': filename,
                    'description': description,
                    'content': content,
                    'size': len(content)
                }
            except Exception as e:
                print(f"テンプレートファイル {filename} の読み込みエラー: {e}")
    
    return templates

# 利用可能なプロンプトテンプレート
PROMPT_TEMPLATES = load_prompt_templates()

@app.route('/')
def index():
    """メインページ"""
    global PROMPT_TEMPLATES
    PROMPT_TEMPLATES = load_prompt_templates()  # 最新の状態を読み込み
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
        
        # アニメランキング記事の場合、画像添付の進捗を更新
        if 'ランキング' in theme or 'ランキング' in prompt_template_file:
            generation_status['progress'] = 70
            generation_status['current_step'] = 'アニメ画像を検索・添付中...'
        
        generation_status['progress'] = 90
        generation_status['current_step'] = '完了処理中...'
        
        if result:
            # 生成履歴を保存
            article_history = {
                'theme': theme,
                'prompt_type': prompt_type,
                'status': status,
                'max_tokens': max_tokens,
                'result': result,
                'created_at': datetime.now().isoformat(),
                'source': 'article_generation'
            }
            
            history_filename = f"article_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(history_filename, 'w', encoding='utf-8') as f:
                json.dump(article_history, f, ensure_ascii=False, indent=2)
            
            generation_status['result'] = result
            generation_status['progress'] = 100
            generation_status['current_step'] = '完了！'
        else:
            generation_status['error'] = '記事の生成に失敗しました。'
            
    except Exception as e:
        generation_status['error'] = f'エラーが発生しました: {str(e)}'
        print(f"記事生成エラー: {e}")
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
    """生成履歴ページ（既存の記事履歴）"""
    return redirect(url_for('generation_history'))

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
        
        generated_at = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
        return render_template('view_article.html', 
                             filename=filename, 
                             content=content,
                             theme=filename.replace('blog_article_', '').replace('.txt', ''),
                             generated_at=generated_at)
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

# プロンプトテンプレート管理機能
@app.route('/prompts')
def prompts():
    """プロンプトテンプレート管理ページ"""
    global PROMPT_TEMPLATES
    PROMPT_TEMPLATES = load_prompt_templates()  # 最新の状態を読み込み
    return render_template('prompts.html', prompt_templates=PROMPT_TEMPLATES)

@app.route('/prompts/view/<template_name>')
def view_prompt(template_name):
    """プロンプトテンプレートの詳細表示"""
    global PROMPT_TEMPLATES
    PROMPT_TEMPLATES = load_prompt_templates()
    
    if template_name not in PROMPT_TEMPLATES:
        flash('テンプレートが見つかりません。', 'error')
        return redirect(url_for('prompts'))
    
    template = PROMPT_TEMPLATES[template_name]
    return render_template('view_prompt.html', template=template, template_name=template_name)

@app.route('/prompts/create', methods=['GET', 'POST'])
def create_prompt():
    """新しいプロンプトテンプレートを作成"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            template_name = data.get('name', '').strip()
            content = data.get('content', '').strip()
            
            if not template_name or not content:
                return jsonify({'error': 'テンプレート名と内容を入力してください。'})
            
            # ファイル名を生成
            filename = f"prompt_{template_name.lower().replace(' ', '_').replace('用', '').replace('テンプレート', '')}.txt"
            
            # ファイル名の重複を避ける
            counter = 1
            original_filename = filename
            while os.path.exists(filename):
                name_part = original_filename.replace('.txt', '')
                filename = f"{name_part}_{counter}.txt"
                counter += 1
            
            # ファイルに保存
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 生成履歴を保存
            history_data = {
                'template_name': template_name,
                'filename': filename,
                'content': content,
                'created_at': datetime.now().isoformat(),
                'file_size': len(content),
                'source': 'manual'
            }
            
            history_filename = f"prompt_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(history_filename, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            flash(f'テンプレート "{template_name}" を作成しました。', 'success')
            return jsonify({'success': True, 'filename': filename})
            
        except Exception as e:
            return jsonify({'error': f'テンプレートの作成でエラーが発生しました: {str(e)}'})
    
    return render_template('create_prompt.html')

@app.route('/prompts/generate', methods=['POST'])
def generate_prompt():
    """AIを使用してプロンプトテンプレートを生成"""
    try:
        data = request.get_json()
        article_theme = data.get('article_theme', '').strip()
        prompt_type = data.get('prompt_type', '').strip()
        target_audience = data.get('target_audience', '').strip()
        content_style = data.get('content_style', '').strip()
        article_length = data.get('article_length', '').strip()
        article_structure = data.get('article_structure', '').strip()
        seo_optimization = data.get('seo_optimization', False)
        keyword_optimization = data.get('keyword_optimization', False)
        meta_description = data.get('meta_description', False)
        heading_structure = data.get('heading_structure', False)
        include_examples = data.get('include_examples', False)
        include_tips = data.get('include_tips', False)
        include_statistics = data.get('include_statistics', False)
        include_call_to_action = data.get('include_call_to_action', False)
        additional_requirements = data.get('additional_requirements', '').strip()
        
        # ランキング設定の値を取得
        ranking_count = data.get('ranking_count', '').strip()
        ranking_criteria = data.get('ranking_criteria', '').strip()
        ranking_format = data.get('ranking_format', '').strip()
        include_ranking_number = data.get('include_ranking_number', False)
        include_product_image = data.get('include_product_image', False)
        include_price = data.get('include_price', False)
        include_rating = data.get('include_rating', False)
        include_comparison = data.get('include_comparison', False)
        ranking_introduction = data.get('ranking_introduction', '').strip()
        
        if not article_theme:
            return jsonify({'error': '記事テーマ例を入力してください。'})
        if not prompt_type:
            return jsonify({'error': 'プロンプトタイプを選択してください。'})
        
        # SEO要件をまとめる
        seo_requirements = []
        if seo_optimization:
            seo_requirements.append("SEO最適化")
        if keyword_optimization:
            seo_requirements.append("キーワード最適化")
        if meta_description:
            seo_requirements.append("メタディスクリプション生成")
        if heading_structure:
            seo_requirements.append("見出し構造の指定")
        
        # コンテンツ要素をまとめる
        content_elements = []
        if include_examples:
            content_elements.append("具体例")
        if include_tips:
            content_elements.append("実践的なTips")
        if include_statistics:
            content_elements.append("統計データ")
        if include_call_to_action:
            content_elements.append("行動喚起")
        
        # ランキング要素をまとめる
        ranking_elements = []
        if include_ranking_number:
            ranking_elements.append("順位番号")
        if include_product_image:
            ranking_elements.append("商品画像の説明")
        if include_price:
            ranking_elements.append("価格情報")
        if include_rating:
            ranking_elements.append("評価・スコア")
        if include_comparison:
            ranking_elements.append("他商品との比較")
        
        # ランキング専用の指示を準備
        ranking_instructions = ""
        if prompt_type == 'ランキング記事' or article_structure == 'ランキング形式':
            ranking_instructions = """
- ランキング形式の場合は、順位、商品名、説明、評価を含む構造化された指示
- 各ランキング項目の詳細な説明と根拠を含める
- ランキングの信頼性と客観性を重視した指示
"""
        
        # ランキング設定の文字列を準備
        ranking_settings_text = ""
        if prompt_type == 'ランキング記事' or article_structure == 'ランキング形式':
            ranking_elements_text = ""
            if ranking_elements:
                ranking_elements_text = "\n".join([f"  - {elem}" for elem in ranking_elements])
            else:
                ranking_elements_text = "  - 基本的なランキング要素"
            
            ranking_settings_text = f"""
- ランキング数: {ranking_count}位
- ランキング基準: {ranking_criteria}
- ランキング形式: {ranking_format}
- ランキング要素: 
{ranking_elements_text}
- ランキング導入文: {ranking_introduction or "標準的な導入文"}
"""
        else:
            ranking_settings_text = "- ランキング形式ではない"
        
        # AI生成用のプロンプトを作成
        ai_prompt = f"""
あなたはプロのプロンプトエンジニアです。
以下の詳細な要件に基づいて、ブログ記事生成用のプロンプトテンプレートを作成してください。

#基本要件
- 記事テーマ例: {article_theme}
- プロンプトタイプ: {prompt_type}
- ターゲット読者: {target_audience or '一般向け'}
- コンテンツスタイル: {content_style or '親しみやすく、分かりやすい'}

#記事設定
- 記事の長さ: {article_length or '標準（2000字程度）'}
- 記事構成: {article_structure or '導入→本文→まとめ'}

#SEO要件
{chr(10).join([f"- {req}" for req in seo_requirements]) if seo_requirements else "- 基本的なSEO考慮"}

#コンテンツ要素
{chr(10).join([f"- {elem}を含める" for elem in content_elements]) if content_elements else "- 基本的な記事構成"}

#ランキング設定
{ranking_settings_text}

#追加要件・特別な指示
{additional_requirements if additional_requirements else "なし"}

#作成するプロンプトの仕様
- 記事生成AI（Perplexity）が理解しやすい形式
- 具体的で実行可能な指示
- 文字数制限や構成の指定
- SEOを意識した内容（指定された場合）
- {{theme}}プレースホルダーを使用（記事のテーマに置き換えられる）
- 指定されたターゲット読者に適した内容
- 指定されたスタイルとトーンに合わせた指示{ranking_instructions}

#出力形式
- 日本語で作成
- 明確な構造（見出し、箇条書き等）
- 実用的で効果的なプロンプト
- 指定された要件をすべて満たす内容

プロンプトテンプレートを作成してください。
"""
        
        # Perplexity APIを使用してプロンプトを生成
        client = PerplexityClient()
        messages = [
            {"role": "user", "content": ai_prompt}
        ]
        
        response = client.chat_completion(messages, model="sonar", max_tokens=2048)
        
        if response:
            generated_content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # 生成された内容をクリーンアップ
            generated_content = generated_content.strip()
            
            # 不要な装飾を削除
            if generated_content.startswith('```'):
                generated_content = generated_content.split('```', 2)[1]
            if generated_content.endswith('```'):
                generated_content = generated_content.rsplit('```', 1)[0]
            
            # 生成履歴を保存
            history_data = {
                'template_name': f"{prompt_type}用テンプレート",
                'article_theme': article_theme,
                'prompt_type': prompt_type,
                'target_audience': target_audience,
                'content_style': content_style,
                'article_length': article_length,
                'article_structure': article_structure,
                'seo_requirements': seo_requirements,
                'content_elements': content_elements,
                'additional_requirements': additional_requirements,
                'ranking_count': ranking_count,
                'ranking_criteria': ranking_criteria,
                'ranking_format': ranking_format,
                'ranking_elements': ranking_elements,
                'ranking_introduction': ranking_introduction,
                'generated_content': generated_content,
                'created_at': datetime.now().isoformat(),
                'source': 'ai_generated'
            }
            
            history_filename = f"prompt_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(history_filename, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            # 生成されたプロンプトをファイルとして保存
            template_name = f"{prompt_type}用テンプレート"
            filename = f"prompt_{template_name.lower().replace(' ', '_').replace('用', '').replace('テンプレート', '')}.txt"
            
            # ファイル名の重複を避ける
            counter = 1
            original_filename = filename
            while os.path.exists(filename):
                name_part = original_filename.replace('.txt', '')
                filename = f"{name_part}_{counter}.txt"
                counter += 1
            
            # ファイルに保存
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(generated_content)
            
            # 履歴データにファイル名を追加
            history_data['filename'] = filename
            with open(history_filename, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            # プロンプトテンプレートを再読み込みして即座に反映
            global PROMPT_TEMPLATES
            PROMPT_TEMPLATES = load_prompt_templates()
            
            return jsonify({
                'success': True,
                'content': generated_content,
                'suggested_name': template_name,
                'filename': filename,
                'message': f'プロンプトテンプレート「{template_name}」が正常に生成され、ファイル「{filename}」として保存されました。'
            })
        else:
            return jsonify({'error': 'AIによるプロンプト生成に失敗しました。'})
            
    except Exception as e:
        return jsonify({'error': f'プロンプト生成でエラーが発生しました: {str(e)}'})

@app.route('/prompts/edit/<template_name>', methods=['GET', 'POST'])
def edit_prompt(template_name):
    """プロンプトテンプレートを編集"""
    global PROMPT_TEMPLATES
    PROMPT_TEMPLATES = load_prompt_templates()
    
    if template_name not in PROMPT_TEMPLATES:
        flash('テンプレートが見つかりません。', 'error')
        return redirect(url_for('prompts'))
    
    template = PROMPT_TEMPLATES[template_name]
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            content = data.get('content', '').strip()
            
            if not content:
                return jsonify({'error': 'テンプレート内容を入力してください。'})
            
            # ファイルを更新
            with open(template['file'], 'w', encoding='utf-8') as f:
                f.write(content)
            
            flash(f'テンプレート "{template["name"]}" を更新しました。', 'success')
            return jsonify({'success': True})
            
        except Exception as e:
            return jsonify({'error': f'テンプレートの更新でエラーが発生しました: {str(e)}'})
    
    return render_template('edit_prompt.html', template=template, template_name=template_name)

@app.route('/prompts/delete/<template_name>', methods=['POST'])
def delete_prompt(template_name):
    """プロンプトテンプレートを削除"""
    global PROMPT_TEMPLATES
    PROMPT_TEMPLATES = load_prompt_templates()
    
    if template_name not in PROMPT_TEMPLATES:
        flash('テンプレートが見つかりません。', 'error')
        return redirect(url_for('prompts'))
    
    template = PROMPT_TEMPLATES[template_name]
    
    try:
        # ファイルを削除
        os.remove(template['file'])
        flash(f'テンプレート "{template["name"]}" を削除しました。', 'success')
    except Exception as e:
        flash(f'テンプレートの削除でエラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('prompts'))

@app.route('/prompts/refresh')
def refresh_prompts():
    """プロンプトテンプレートを再読み込み"""
    global PROMPT_TEMPLATES
    PROMPT_TEMPLATES = load_prompt_templates()
    flash('プロンプトテンプレートを再読み込みしました。', 'success')
    return redirect(url_for('prompts'))

@app.route('/prompts/restore-from-history')
def restore_prompts_from_history():
    """生成履歴からプロンプトテンプレートを復元"""
    try:
        restored_count = 0
        
        # プロンプト生成履歴を検索
        for filename in os.listdir('.'):
            if filename.startswith('prompt_history_') and filename.endswith('.json'):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        history_data = json.load(f)
                    
                    # AI生成されたプロンプトのみを対象
                    if history_data.get('source') == 'ai_generated':
                        generated_content = history_data.get('generated_content', '')
                        template_name = history_data.get('template_name', '')
                        
                        if generated_content and template_name:
                            # ファイル名を生成
                            filename_base = f"prompt_{template_name.lower().replace(' ', '_').replace('用', '').replace('テンプレート', '')}.txt"
                            
                            # ファイルが存在しない場合のみ作成
                            if not os.path.exists(filename_base):
                                with open(filename_base, 'w', encoding='utf-8') as f:
                                    f.write(generated_content)
                                restored_count += 1
                                print(f"復元されたテンプレート: {filename_base}")
                
                except Exception as e:
                    print(f"履歴ファイル {filename} の処理エラー: {e}")
        
        # プロンプトテンプレートを再読み込み
        global PROMPT_TEMPLATES
        PROMPT_TEMPLATES = load_prompt_templates()
        
        if restored_count > 0:
            flash(f'{restored_count}個のプロンプトテンプレートを履歴から復元しました。', 'success')
        else:
            flash('復元可能なプロンプトテンプレートはありませんでした。', 'info')
            
    except Exception as e:
        flash(f'プロンプトテンプレートの復元でエラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('prompts'))

# プロンプト評価・改善機能
@app.route('/prompts/evaluate/<template_name>', methods=['GET', 'POST'])
def evaluate_prompt(template_name):
    """プロンプトテンプレートを評価・改善"""
    global PROMPT_TEMPLATES
    PROMPT_TEMPLATES = load_prompt_templates()
    
    if template_name not in PROMPT_TEMPLATES:
        flash('テンプレートが見つかりません。', 'error')
        return redirect(url_for('prompts'))
    
    template = PROMPT_TEMPLATES[template_name]
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            evaluation_type = data.get('evaluation_type', 'general')
            specific_feedback = data.get('specific_feedback', '')
            
            # 評価用のプロンプトを作成
            evaluation_prompts = {
                'general': 'このプロンプトテンプレートを全体的に改善し、より効果的で実用的なものにしてください。',
                'clarity': 'このプロンプトテンプレートをより明確で分かりやすい指示に改善してください。',
                'structure': 'このプロンプトテンプレートの構造を改善し、より論理的で実行しやすいものにしてください。',
                'seo': 'このプロンプトテンプレートをSEO最適化の観点から改善してください。',
                'engagement': 'このプロンプトテンプレートを読者の興味を引く記事生成に改善してください。',
                'custom': specific_feedback
            }
            
            evaluation_prompt = evaluation_prompts.get(evaluation_type, evaluation_prompts['general'])
            
            # AIを使用してプロンプトを評価・改善
            client = PerplexityClient()
            messages = [
                {"role": "user", "content": f"""
以下のプロンプトテンプレートを評価・改善してください。

#評価・改善指示
{evaluation_prompt}

#元のプロンプトテンプレート
{template['content']}

#改善要件
- 元のプロンプトの意図と目的を保持
- より明確で実行可能な指示に改善
- 構造化された形式を維持
- {{theme}}プレースホルダーを保持
- 実用的で効果的なプロンプトに改善

#出力形式
改善されたプロンプトテンプレートを出力してください。
改善点の説明も含めてください。
"""}
            ]
            
            response = client.chat_completion(messages, model="sonar", max_tokens=2048)
            
            if response:
                improved_content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # 改善された内容をクリーンアップ
                improved_content = improved_content.strip()
                
                # 不要な装飾を削除
                if improved_content.startswith('```'):
                    improved_content = improved_content.split('```', 2)[1]
                if improved_content.endswith('```'):
                    improved_content = improved_content.rsplit('```', 1)[0]
                
                # 評価履歴を保存
                evaluation_history = {
                    'template_name': template_name,
                    'template_file': template['file'],
                    'evaluation_type': evaluation_type,
                    'specific_feedback': specific_feedback,
                    'original_content': template['content'],
                    'improved_content': improved_content,
                    'created_at': datetime.now().isoformat(),
                    'source': 'ai_evaluation'
                }
                
                history_filename = f"evaluation_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(history_filename, 'w', encoding='utf-8') as f:
                    json.dump(evaluation_history, f, ensure_ascii=False, indent=2)
                
                return jsonify({
                    'success': True,
                    'improved_content': improved_content,
                    'original_content': template['content']
                })
            else:
                return jsonify({'error': 'プロンプトの評価・改善に失敗しました。'})
                
        except Exception as e:
            return jsonify({'error': f'プロンプトの評価・改善でエラーが発生しました: {str(e)}'})
    
    return render_template('evaluate_prompt.html', template=template, template_name=template_name)

# 生成履歴の保存と管理
@app.route('/generation-history')
def generation_history():
    """生成履歴ページ（統合版）"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # フィルタリングパラメータ
    type_filter = request.args.get('type', '')
    date_filter = request.args.get('date', '')
    search_filter = request.args.get('search', '')
    
    history_items = []
    
    # 記事生成履歴
    for filename in os.listdir('.'):
        if filename.startswith('blog_article_') and filename.endswith('.txt'):
            try:
                file_path = filename
                file_size = os.path.getsize(filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(filename))
                
                # ファイル名からテーマを抽出
                theme = filename.replace('blog_article_', '').replace('.txt', '')
                
                # フィルタリング
                if type_filter and type_filter != 'article':
                    continue
                    
                if date_filter:
                    if date_filter == 'today' and file_time.date() != datetime.now().date():
                        continue
                    elif date_filter == 'week' and (datetime.now() - file_time).days > 7:
                        continue
                    elif date_filter == 'month' and (datetime.now() - file_time).days > 30:
                        continue
                    elif date_filter == 'year' and (datetime.now() - file_time).days > 365:
                        continue
                
                if search_filter and search_filter.lower() not in theme.lower():
                    continue
                
                # ファイル内容のプレビューを取得
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    preview_content = content[:200] + '...' if len(content) > 200 else content
                
                history_items.append({
                    'filename': filename,
                    'title': f'記事: {theme}',
                    'type': 'article',
                    'type_display': '記事生成',
                    'theme': theme,
                    'file_size': file_size,
                    'created_at': file_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'preview_content': preview_content,
                    'file_path': file_path,
                    'can_view_local': True,
                    'post_url': None
                })
            except Exception as e:
                print(f"記事ファイル {filename} の読み込みエラー: {e}")
    
    # 記事履歴（JSONファイル）
    for filename in os.listdir('.'):
        if filename.startswith('article_history_') and filename.endswith('.json'):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                file_time = datetime.fromisoformat(history_data.get('created_at', ''))
                theme = history_data.get('theme', '')
                
                # フィルタリング
                if type_filter and type_filter != 'article':
                    continue
                    
                if date_filter:
                    if date_filter == 'today' and file_time.date() != datetime.now().date():
                        continue
                    elif date_filter == 'week' and (datetime.now() - file_time).days > 7:
                        continue
                    elif date_filter == 'month' and (datetime.now() - file_time).days > 30:
                        continue
                    elif date_filter == 'year' and (datetime.now() - file_time).days > 365:
                        continue
                
                if search_filter and search_filter.lower() not in theme.lower():
                    continue
                
                result = history_data.get('result', {})
                preview_content = f"タイトル: {result.get('title', '')}\nステータス: {result.get('status', '')}\n投稿ID: {result.get('post_id', '')}\nURL: {result.get('post_url', '')}"
                
                history_items.append({
                    'filename': filename,
                    'title': f'記事: {theme}',
                    'type': 'article',
                    'type_display': '記事生成',
                    'theme': theme,
                    'file_size': os.path.getsize(filename),
                    'created_at': file_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'preview_content': preview_content,
                    'can_view_local': False,
                    'post_url': result.get('post_url')
                })
            except Exception as e:
                print(f"記事履歴ファイル {filename} の読み込みエラー: {e}")
    
    # プロンプト生成履歴
    for filename in os.listdir('.'):
        if filename.startswith('prompt_history_') and filename.endswith('.json'):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                file_time = datetime.fromisoformat(history_data.get('created_at', ''))
                
                # フィルタリング
                if type_filter and type_filter != 'prompt':
                    continue
                    
                if date_filter:
                    if date_filter == 'today' and file_time.date() != datetime.now().date():
                        continue
                    elif date_filter == 'week' and (datetime.now() - file_time).days > 7:
                        continue
                    elif date_filter == 'month' and (datetime.now() - file_time).days > 30:
                        continue
                    elif date_filter == 'year' and (datetime.now() - file_time).days > 365:
                        continue
                
                if search_filter:
                    template_name = history_data.get('template_name', '')
                    if search_filter.lower() not in template_name.lower():
                        continue
                
                preview_content = history_data.get('generated_content', '')[:200] + '...' if len(history_data.get('generated_content', '')) > 200 else history_data.get('generated_content', '')
                
                history_items.append({
                    'filename': filename,
                    'title': f'プロンプト: {history_data.get("template_name", "")}',
                    'type': 'prompt',
                    'type_display': 'プロンプト生成',
                    'template_name': history_data.get('template_name', ''),
                    'file_size': os.path.getsize(filename),
                    'created_at': file_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'preview_content': preview_content
                })
            except Exception as e:
                print(f"プロンプト履歴ファイル {filename} の読み込みエラー: {e}")
    
    # 評価履歴
    for filename in os.listdir('.'):
        if filename.startswith('evaluation_history_') and filename.endswith('.json'):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                file_time = datetime.fromisoformat(history_data.get('created_at', ''))
                
                # フィルタリング
                if type_filter and type_filter != 'evaluation':
                    continue
                    
                if date_filter:
                    if date_filter == 'today' and file_time.date() != datetime.now().date():
                        continue
                    elif date_filter == 'week' and (datetime.now() - file_time).days > 7:
                        continue
                    elif date_filter == 'month' and (datetime.now() - file_time).days > 30:
                        continue
                    elif date_filter == 'year' and (datetime.now() - file_time).days > 365:
                        continue
                
                if search_filter:
                    template_name = history_data.get('template_name', '')
                    if search_filter.lower() not in template_name.lower():
                        continue
                
                preview_content = history_data.get('improved_content', '')[:200] + '...' if len(history_data.get('improved_content', '')) > 200 else history_data.get('improved_content', '')
                
                history_items.append({
                    'filename': filename,
                    'title': f'評価: {history_data.get("template_name", "")}',
                    'type': 'evaluation',
                    'type_display': 'プロンプト評価',
                    'template_name': history_data.get('template_name', ''),
                    'file_size': os.path.getsize(filename),
                    'created_at': file_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'preview_content': preview_content
                })
            except Exception as e:
                print(f"評価履歴ファイル {filename} の読み込みエラー: {e}")
    
    # 作成日時でソート（新しい順）
    history_items.sort(key=lambda x: x['created_at'], reverse=True)
    
    # ページネーション
    total_items = len(history_items)
    total_pages = (total_items + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_items = history_items[start_idx:end_idx]
    
    # ページネーション情報（テンプレート側での関数呼び出しを避けるため配列を渡す）
    page_numbers = list(range(max(1, page - 2), min(total_pages + 1, page + 3))) if total_pages > 0 else []
    pagination = {
        'page': page,
        'pages': total_pages,
        'per_page': per_page,
        'total': total_items,
        'items': paginated_items,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page < total_pages else None,
        'page_numbers': page_numbers
    }
    
    return render_template('generation_history.html', 
                         history_items=paginated_items, 
                         pagination=pagination)

@app.route('/history/detail/<filename>')
def view_history_detail(filename):
    """生成履歴の詳細表示"""
    try:
        file_path = os.path.join('.', filename)
        if not os.path.exists(file_path):
            flash('履歴ファイルが見つかりません。', 'error')
            return redirect(url_for('generation_history'))
        
        if filename.startswith('blog_article_'):
            # 記事ファイルの場合
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            theme = filename.replace('blog_article_', '').replace('.txt', '')
            history_data = {
                'type': 'article',
                'title': f'記事: {theme}',
                'theme': theme,
                'content': content,
                'created_at': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'),
                'file_size': os.path.getsize(file_path)
            }
        elif filename.startswith('article_history_'):
            # 記事履歴JSONファイルの場合
            with open(file_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            history_data['type'] = 'article'
            history_data['title'] = f'記事: {history_data.get("theme", "")}'
            history_data['file_size'] = os.path.getsize(file_path)
            history_data['created_at'] = datetime.fromisoformat(history_data.get('created_at', '')).strftime('%Y-%m-%d %H:%M:%S')
        else:
            # JSONファイルの場合
            with open(file_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            history_data['type'] = 'prompt' if filename.startswith('prompt_history_') else 'evaluation'
            history_data['title'] = f"{'プロンプト' if history_data['type'] == 'prompt' else '評価'}: {history_data.get('template_name', '')}"
            history_data['file_size'] = os.path.getsize(file_path)
        
        return render_template('view_history_detail.html', 
                             filename=filename, 
                             history_data=history_data)
    except Exception as e:
        flash(f'履歴ファイルの読み込みでエラーが発生しました: {str(e)}', 'error')
        return redirect(url_for('generation_history'))

@app.route('/history/delete/<filename>', methods=['POST'])
def delete_history_item(filename):
    """生成履歴アイテムを削除"""
    try:
        file_path = os.path.join('.', filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('履歴を削除しました。', 'success')
        else:
            flash('履歴ファイルが見つかりません。', 'error')
    except Exception as e:
        flash(f'履歴の削除でエラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('generation_history'))

# プロンプトプレビュー機能
@app.route('/prompts/preview/<template_name>')
def preview_prompt(template_name):
    """プロンプトテンプレートのプレビュー"""
    global PROMPT_TEMPLATES
    PROMPT_TEMPLATES = load_prompt_templates()
    
    if template_name not in PROMPT_TEMPLATES:
        flash('テンプレートが見つかりません。', 'error')
        return redirect(url_for('prompts'))
    
    template = PROMPT_TEMPLATES[template_name]
    
    # サンプルテーマでプレビュー
    sample_theme = "健康な食事の作り方"
    preview_content = template['content'].replace('{theme}', sample_theme)
    
    return render_template('preview_prompt.html', 
                         template=template, 
                         template_name=template_name,
                         preview_content=preview_content,
                         sample_theme=sample_theme)

@app.route('/preview/history/<filename>')
def preview_from_history(filename):
    """履歴から記事プレビュー（投稿せずにHTML表示）"""
    try:
        # テーマ推定
        theme = filename.replace('blog_article_', '').replace('.txt', '')
        # 既存テンプレートから最も近いものを選ぶ（ランキング優先）
        global PROMPT_TEMPLATES
        PROMPT_TEMPLATES = load_prompt_templates()
        tmpl_file = 'prompt_アニメランキングSEO最適化.txt' if 'ランキング' in theme else 'prompt_template.txt'
        tool = IntegratedBlogTool()
        result = tool.generate_article_content(theme, tmpl_file, 2048)
        if not result:
            flash('プレビューの生成に失敗しました。', 'error')
            return redirect(url_for('generation_history'))
        return render_template('view_article.html', 
                             filename=filename,
                             content=result['html'],
                             theme=result['title'],
                             generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        flash(f'プレビュー生成でエラーが発生しました: {str(e)}', 'error')
        return redirect(url_for('generation_history'))

@app.route('/prompts/preview/generate', methods=['POST'])
def generate_preview():
    """プレビュー用の記事を生成"""
    try:
        data = request.get_json()
        template_name = data.get('template_name', '').strip()
        theme = data.get('theme', '').strip()
        
        if not template_name or not theme:
            return jsonify({'error': 'テンプレート名とテーマを入力してください。'})
        
        global PROMPT_TEMPLATES
        PROMPT_TEMPLATES = load_prompt_templates()
        
        if template_name not in PROMPT_TEMPLATES:
            return jsonify({'error': 'テンプレートが見つかりません。'})
        
        template = PROMPT_TEMPLATES[template_name]
        
        # プロンプトテンプレートを適用
        prompt_content = template['content'].replace('{theme}', theme)
        
        # Perplexity APIを使用して記事を生成
        client = PerplexityClient()
        messages = [
            {"role": "user", "content": prompt_content}
        ]
        
        response = client.chat_completion(messages, model="sonar", max_tokens=1024)
        
        if response:
            generated_article = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            return jsonify({
                'success': True,
                'article': generated_article
            })
        else:
            return jsonify({'error': '記事の生成に失敗しました。'})
            
    except Exception as e:
        return jsonify({'error': f'プレビュー生成でエラーが発生しました: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
