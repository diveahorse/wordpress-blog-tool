import os
import requests
import base64
import sys
import re
import json
from datetime import datetime
from dotenv import load_dotenv
from perplexity_client import PerplexityClient, create_blog_article
from urllib.parse import urljoin, urlparse
import time

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
        
        # 画像キャッシュ（永続化）
        self.image_cache = {}
        self._image_cache_path = os.path.join(os.getcwd(), 'image_cache.json')
        try:
            if os.path.exists(self._image_cache_path):
                with open(self._image_cache_path, 'r', encoding='utf-8') as f:
                    self.image_cache = json.load(f)
        except Exception as e:
            print(f"画像キャッシュ読み込みエラー: {e}")
    
    def search_anime_image(self, anime_title):
        """
        アニメの公式画像を検索・取得
        
        Args:
            anime_title (str): アニメタイトル
        
        Returns:
            dict|None: { 'url': 画像URL, 'source': 参照元URL or None }
        """
        try:
            # キャッシュから画像を取得
            if anime_title in self.image_cache:
                print(f"キャッシュから画像を取得: {anime_title}")
                cached = self.image_cache[anime_title]
                if isinstance(cached, dict):
                    return cached
                return {'url': cached, 'source': None}

            # シンプルな単一クエリで高速化
            search_queries = [
                f"{anime_title} 公式サイト 画像 アニメ"
            ]
            
            for query in search_queries:
                try:
                    messages = [
                        {
                            "role": "user", 
                            "content": f"以下のアニメの公式サイトや公式画像のURLを教えてください。可能であれば、高品質な画像の直接リンクも含めてください：{query}"
                        }
                    ]
                    
                    response = self.perplexity_client.chat_completion(messages, model="sonar", max_tokens=1000)
                    
                    if response and 'choices' in response:
                        content = response['choices'][0]['message']['content']
                        
                    # URLを抽出
                    urls = re.findall(r'https?://[^\s<>"]+', content)

                    # ブロックリスト（日本で一般的でない/不適切ソースを除外）
                    blocked_domains = [
                        'crunchyroll', 'pinterest', 'facebook', 'twitter', 'x.com', 'instagram',
                        'myanimelist', 'anilist', 'kitsu', 'fandom.com', 'tumblr', 'deviantart'
                    ]
                        
                    # 画像URLを探す（直接リンク優先。ブロックドメインは除外）
                    for url in urls:
                        lower = url.lower()
                        if any(b in lower for b in blocked_domains):
                            continue
                        if any(ext in lower for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                            if self._is_valid_image_url(url):
                                result_obj = {'url': url, 'source': None}
                                self.image_cache[anime_title] = result_obj
                                self._save_image_cache()
                                print(f"画像URLを発見: {url}")
                                return result_obj
                        
                    # 公式サイトのURLをスコアリングして探索
                    def site_score(u: str) -> int:
                        s = 0
                        lu = u.lower()
                        if any(b in lu for b in blocked_domains):
                            s -= 100
                        if 'official' in lu:
                            s += 20
                        if lu.endswith('.jp') or '.jp/' in lu:
                            s += 10
                        if any(k in lu for k in ['anime', '/tv', '/news']):
                            s += 4
                        # SNS/動画サイトは避ける
                        if any(k in lu for k in ['youtube', 'tiktok', 'instagram', 'x.com', 'twitter']):
                            s -= 20
                        return s

                    candidate_sites = sorted(urls, key=site_score, reverse=True)
                    for url in candidate_sites:
                        if any(b in url.lower() for b in blocked_domains):
                            continue
                        image_url = self._extract_image_from_official_site(url, anime_title)
                        if image_url:
                            result_obj = {'url': image_url, 'source': url}
                            self.image_cache[anime_title] = result_obj
                            self._save_image_cache()
                            print(f"公式サイトから画像を取得: {image_url}")
                            return result_obj
                    
                    # 待機短縮
                    time.sleep(0.05)
                    
                except Exception as e:
                    print(f"検索クエリ '{query}' でエラーが発生: {e}")
                    continue
            
            print(f"画像が見つかりませんでした: {anime_title}")
            return None
            
        except Exception as e:
            print(f"画像検索エラー: {e}")
            return None
    
    def _is_valid_image_url(self, url):
        """画像URLの妥当性をチェック"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.head(url, headers=headers, timeout=5)
            content_type = response.headers.get('content-type', '').lower()
            return 'image' in content_type and response.status_code == 200
        except Exception as e:
            print(f"画像URL検証エラー: {e}")
            return False
    
    def _extract_image_from_official_site(self, site_url, anime_title):
        """公式サイトから画像を抽出
        優先順位:
        1) og:image / twitter:image / link[rel=image_src]
        2) key visual っぽいファイル名を優先 (keyvisual/kv/main/visual)
        3) それ以外の <img> だが、イベント/ロゴ/バナー/サムネは除外
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(site_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            html = response.text

            candidates = []

            def add_candidate(url, source_tag):
                try:
                    absolute = url if url.startswith('http') else urljoin(site_url, url)
                    candidates.append((absolute, source_tag))
                except Exception:
                    pass

            # 1) メタタグ優先
            og_patterns = [
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+name=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']'
            ]
            for pattern in og_patterns:
                for m in re.findall(pattern, html, re.IGNORECASE):
                    add_candidate(m, 'meta')

            # 2) 通常のimg / background-image / data-src
            img_patterns = [
                r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif))["\'][^>]*>',
                r'<img[^>]+data-src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif))["\'][^>]*>',
                r'background-image:\s*url\(["\']?([^"\')\s]+\.(?:jpg|jpeg|png|webp|gif))["\']?\)'
            ]
            for pattern in img_patterns:
                for m in re.findall(pattern, html, re.IGNORECASE):
                    add_candidate(m, 'img')

            # 候補をスコアリング
            def score(url, source_tag):
                lower = url.lower()
                s = 0
                # メタの方が強い
                if source_tag == 'meta':
                    s += 30
                # キービジュアルを示唆
                if any(k in lower for k in ['keyvisual', 'key-visual', 'kv', 'mainvisual', 'main-visual', 'visual', 'hero']):
                    s += 50
                # 公式サイトっぽいCDN/アセット
                if any(k in lower for k in ['assets', '/img/', '/images/', '/wp-content/uploads/']):
                    s += 10
                # 除外ワード
                if any(b in lower for b in ['event', 'exhibit', 'exhibition', 'banner', 'bnr', 'logo', 'icon', 'thumb', 'thumbnail', 'sprite', 'button', 'campaign']):
                    s -= 60
                # 画像拡張子ごとの優先 (webp/png > jpg)
                if lower.endswith('.webp'):
                    s += 8
                if lower.endswith('.png'):
                    s += 5
                # クエリでサイズが大きそう
                if any(k in lower for k in ['1200', '1920', '2000', 'ogp']):
                    s += 6
                return s

            ranked = sorted(candidates, key=lambda t: score(t[0], t[1]), reverse=True)

            for url, tag in ranked:
                if self._is_valid_image_url(url):
                    return url
            
            return None
            
        except Exception as e:
            print(f"公式サイトからの画像抽出エラー: {e}")
            return None
    
    def add_images_to_anime_ranking(self, content):
        """
        アニメランキング記事に画像を追加
        
        Args:
            content (str): 元の記事コンテンツ
        
        Returns:
            str: 画像が追加された記事コンテンツ
        """
        updated_content = content
        found_images = 0

        # HTMLかどうかを判定
        is_html = bool(re.search(r'<\s*h3\b', content, flags=re.IGNORECASE))

        if is_html:
            # <h3>第X位: 作品名</h3> を検出して直後に挿入
            heading_pattern = re.compile(r'(<h3[^>]*>\s*第(\d+)位[：:]\s*([^<]+?)\s*</h3>)', re.IGNORECASE)

            def replace_heading(match):
                nonlocal found_images
                full_heading = match.group(1)
                rank = match.group(2)
                title = match.group(3).strip()

                print(f"第{rank}位「{title}」の画像を検索中（HTML）...")
                result = self.search_anime_image(title)
                if not result:
                    print(f"✗ 第{rank}位「{title}」の画像が見つかりませんでした")
                    return full_heading

                image_url = result['url']
                source_url = result.get('source')
                caption = f"{title} 公式画像"
                if source_url:
                    caption += f'｜出典: <a href="{source_url}" target="_blank" rel="nofollow noopener">公式サイト</a>'

                img_html = (
                    f'\n<div class="anime-image">\n'
                    f'<img src="{image_url}" alt="{title} 公式画像" loading="lazy">\n'
                    f'<p class="anime-image-caption">{caption}</p>\n'
                    f'</div>\n'
                )
                found_images += 1
                print(f"✓ 第{rank}位「{title}」の画像を追加しました")
                time.sleep(0.5)
                return full_heading + img_html

            updated_content = heading_pattern.sub(replace_heading, updated_content)
        else:
            # プレーンテキスト/Markdownの見出しから抽出
            anime_titles = []
            for line in content.split('\n'):
                match = re.search(r'第(\d+)位[：:]\s*(.+?)(?:\n|$)', line)
                if match:
                    rank = match.group(1)
                    title = match.group(2).strip()
                    title = re.sub(r'<[^>]+>', '', title)
                    anime_titles.append((rank, title))

            print(f"アニメランキング記事を検出しました。{len(anime_titles)}作品の画像を検索します...")

            for i, (rank, title) in enumerate(anime_titles, 1):
                print(f"第{rank}位「{title}」の画像を検索中... ({i}/{len(anime_titles)})")
                result = self.search_anime_image(title)
                if result:
                    image_url = result['url']
                    source_url = result.get('source')
                    caption = f"{title} 公式画像"
                    if source_url:
                        caption += f'｜出典: <a href="{source_url}" target="_blank" rel="nofollow noopener">公式サイト</a>'
                    img_html = (
                        f'\n<div class="anime-image">\n'
                        f'<img src="{image_url}" alt="{title} 公式画像" loading="lazy">\n'
                        f'<p class="anime-image-caption">{caption}</p>\n'
                        f'</div>\n'
                    )
                    # 見出しブロックの直後に挿入（Markdown用の簡易処理）
                    pattern = rf'(第{rank}位[：:]\s*{re.escape(title)}\s*)'
                    updated_content = re.sub(pattern, rf'\1{img_html}', updated_content, count=1)
                    print(f"✓ 第{rank}位「{title}」の画像を追加しました")
                    found_images += 1
                    time.sleep(0.5)
                else:
                    print(f"✗ 第{rank}位「{title}」の画像が見つかりませんでした")

        print(f"画像添付が完了しました。合計 {found_images} 件の画像を追加しました。")
        return updated_content

    def generate_article_content(self, theme, prompt_template_file="prompt_template.txt", max_tokens=4096):
        """記事本文のみ生成（投稿はしない）"""
        print(f"プレビュー用に記事本文を生成中... テーマ: {theme}")
        raw_article = create_blog_article(theme, self.perplexity_client, prompt_template_file, max_tokens)
        if not raw_article or not str(raw_article).strip():
            return None
        article_text = str(raw_article).strip()
        if '```' in article_text:
            start_idx = article_text.find('```')
            end_idx = article_text.rfind('```')
            if end_idx > start_idx:
                inner = article_text[start_idx + 3:end_idx].strip()
                first_nl = inner.find('\n')
                if first_nl != -1:
                    first_line = inner[:first_nl].strip().lower()
                    if first_line in ('html', 'markdown', 'md'):
                        inner = inner[first_nl + 1:].strip()
                article_text = inner
        title = ""
        md_title_match = re.search(r'^#\s+(.+)$', article_text, re.MULTILINE)
        if md_title_match:
            title = md_title_match.group(1).strip()
        else:
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', article_text, flags=re.IGNORECASE | re.DOTALL)
            if h1_match:
                title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
        if not title:
            title = f"{theme}について"
        is_html = bool(re.search(r'<(h1|h2|h3|h4|p|ul|ol|div|section|article)\b', article_text, flags=re.IGNORECASE))
        if is_html:
            body_html = re.sub(r'^\s*<h1[^>]*>.*?</h1>\s*', '', article_text, flags=re.IGNORECASE | re.DOTALL)
            html_content = body_html.strip()
        else:
            lines = article_text.split('\n')
            content_lines = []
            in_content = False
            for ln in lines:
                if re.match(r'^\s*##\s+', ln) or re.match(r'^\s*###\s+', ln) or ln.startswith('- ') or re.match(r'^\s*\d+\. ', ln):
                    in_content = True
                    content_lines.append(ln)
                elif in_content:
                    content_lines.append(ln)
            content_md = '\n'.join([l for l in content_lines if l.strip()])
            if not content_md.strip():
                content_md = article_text
            html_content = self._convert_to_html(content_md)
        # ランキング画像挿入と目次
        if ('ランキング' in theme) or ('ランキング' in prompt_template_file) or re.search(r'第\d+位', html_content):
            html_content = self.add_images_to_anime_ranking(html_content)
            html_content = self._inject_rank_title_toc(html_content)
        html_content = self._postprocess_html(html_content)
        return {'title': title, 'html': html_content}

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
            raw_article = create_blog_article(theme, self.perplexity_client, prompt_template_file, max_tokens)
            
            if not raw_article or not str(raw_article).strip():
                print("記事の生成に失敗しました。コンテンツが空です。")
                return None
            
            article_text = str(raw_article).strip()
            
            # コードフェンス（```）で囲まれている場合は中身を抽出
            if '```' in article_text:
                start_idx = article_text.find('```')
                end_idx = article_text.rfind('```')
                if end_idx > start_idx:
                    inner = article_text[start_idx + 3:end_idx].strip()
                    # 先頭に言語指定がある場合は除去
                    first_nl = inner.find('\n')
                    if first_nl != -1:
                        first_line = inner[:first_nl].strip().lower()
                        if first_line in ('html', 'markdown', 'md'):
                            inner = inner[first_nl + 1:].strip()
                    article_text = inner
            
            # タイトル抽出
            title = ""
            md_title_match = re.search(r'^#\s+(.+)$', article_text, re.MULTILINE)
            if md_title_match:
                title = md_title_match.group(1).strip()
            else:
                h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', article_text, flags=re.IGNORECASE | re.DOTALL)
                if h1_match:
                    # タグを除去
                    title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
            if not title:
                # 最初の非空行から推測
                for ln in article_text.splitlines():
                    clean_ln = ln.strip()
                    if not clean_ln or clean_ln.startswith('```'):
                        continue
                    # タグを除去
                    guess = re.sub(r'<[^>]+>', '', clean_ln).strip()
                    if guess:
                        title = guess
                        break
            if not title:
                title = f"{theme}について"
            
            # 本文抽出とHTML判定
            is_html = bool(re.search(r'<(h1|h2|h3|h4|p|ul|ol|div|section|article)\b', article_text, flags=re.IGNORECASE))
            if is_html:
                # 先頭のH1があれば除去
                body_html = re.sub(r'^\s*<h1[^>]*>.*?</h1>\s*', '', article_text, flags=re.IGNORECASE | re.DOTALL)
                html_content = body_html.strip()
            else:
                # Markdownから本文を抽出
                lines = article_text.split('\n')
                content_lines = []
                in_content = False
                for ln in lines:
                    if re.match(r'^\s*##\s+', ln) or re.match(r'^\s*###\s+', ln) or ln.startswith('- ') or re.match(r'^\s*\d+\. ', ln):
                        in_content = True
                        content_lines.append(ln)
                    elif in_content:
                        content_lines.append(ln)
                content_md = '\n'.join([l for l in content_lines if l.strip()])
                if not content_md.strip():
                    # フォールバックとして全文を使用
                    content_md = article_text
                html_content = self._convert_to_html(content_md)
            
            # アニメランキング記事の場合、画像を追加（HTMLに対して実施）
            if ('ランキング' in theme) or ('ランキング' in prompt_template_file) or re.search(r'第\d+位', html_content):
                print("アニメランキング記事を検出しました。画像を追加中...")
                html_content = self.add_images_to_anime_ranking(html_content)

                # 目次（順位＋作品名のみ）を自動生成して挿入
                html_content = self._inject_rank_title_toc(html_content)
            
            # 最終HTML整形（SEO/UX）
            html_content = self._postprocess_html(html_content)

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

    def _inject_rank_title_toc(self, html_content: str) -> str:
        """<h3>第X位: 作品名</h3> をもとに、順位＋作品名のみの目次を生成して挿入。
        - 各<h3>に安定したidを付与し、<h2>目次</h2>配下の<ul>でリンクを作成。
        - すでに存在する"目次"ブロックがあれば置き換える。
        - 挿入位置は <h2>ランキング紹介</h2> の直後。なければ最初の<h2>の直後。
        """
        try:
            content = html_content

            # 既存の目次ブロックを削除（<h2>.*目次.*</h2> ～ 次の<h2|h3>まで）
            content = re.sub(r'<h2[^>]*>[^<]*目次[^<]*</h2>[\s\S]*?(?=(<h2|<h3))', '', content, flags=re.IGNORECASE)

            # <h3>見出しを列挙し、idを付与
            def slugify(text: str) -> str:
                text = re.sub(r'\s+', '-', text)
                text = re.sub(r'[^\w\-一-龯ぁ-んァ-ヶー]', '', text)
                return text.lower()

            headings = []  # (rank_num, title_text, id)

            def add_id_to_h3(match):
                full = match.group(0)
                before = match.group(1)  # <h3 ...>
                all_text = match.group(2)  # 第X位: 作品名
                rank_num = match.group(3)
                title = match.group(4).strip()

                # id生成
                base_id = f"rank-{rank_num}-{slugify(title)}"
                # 既存idが無ければ付与
                if re.search(r'\sid=\"[^\"]+\"', before, flags=re.IGNORECASE):
                    h3_open = before
                    # 既存idを取得
                    id_match = re.search(r'\sid=\"([^\"]+)\"', before, flags=re.IGNORECASE)
                    element_id = id_match.group(1) if id_match else base_id
                else:
                    # 閉じる'>'直前に id を挿入
                    h3_open = re.sub(r'>\s*$', f' id="{base_id}">', before)
                    element_id = base_id

                headings.append((rank_num, title, element_id))
                return f"{h3_open}{all_text}</h3>"

            h3_pattern = re.compile(r'(<h3[^>]*>)(第(\d+)位[：:]\s*([^<]+))</h3>', re.IGNORECASE)
            content = h3_pattern.sub(add_id_to_h3, content)

            if not headings:
                return content

            # TOCを作成
            toc_items = ''.join([f'<li><a href="#{hid}">第{num}位: {title}</a></li>' for num, title, hid in headings])
            toc_html = f'<h2>目次</h2>\n<nav class="toc" aria-label="目次">\n<ul>\n{toc_items}\n</ul>\n</nav>\n'

            # ランキング紹介の直後に挿入。なければ最初の<h2>の直後
            inserted = False
            def insert_after(pattern):
                nonlocal content, inserted
                m = re.search(pattern, content, flags=re.IGNORECASE)
                if m:
                    idx = m.end()
                    content = content[:idx] + '\n' + toc_html + content[idx:]
                    inserted = True

            insert_after(r'<h2[^>]*>[^<]*ランキング[^<]*紹介[^<]*</h2>')
            if not inserted:
                insert_after(r'<h2[^>]*>.*?</h2>')
            if not inserted:
                # どこにも<h2>が無い場合は先頭に
                content = toc_html + content

            return content
        except Exception as e:
            print(f"目次挿入エラー: {e}")
            return html_content

    def _save_image_cache(self):
        try:
            with open(self._image_cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.image_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"画像キャッシュ保存エラー: {e}")

    def _postprocess_html(self, html_content: str) -> str:
        """HTML投稿前の最終整形。
        - 外部リンクに rel と noopener 付与
        - 画像に loading="lazy" を付与
        """
        try:
            html = html_content
            # 画像のlazy
            html = re.sub(r'<img(?![^>]*\sloading=)[^>]*>',
                          lambda m: m.group(0).rstrip('>') + ' loading="lazy">', html, flags=re.IGNORECASE)
            # 外部リンクへ rel 付与（すでにある場合は保持）
            def add_rel(match):
                tag = match.group(0)
                if 'rel=' in tag:
                    return tag
                return tag[:-1] + ' rel="nofollow noopener noreferrer">'
            html = re.sub(r'<a\s+[^>]*href=\"https?://[^\"]+\"[^>]*>', add_rel, html, flags=re.IGNORECASE)
            return html
        except Exception as e:
            print(f"HTML後処理エラー: {e}")
            return html_content
    
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