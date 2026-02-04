#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Spirits - Update script for the repository spirit
"""

import json
import datetime
import random
import re
import os
import sys
import subprocess
import urllib.request
import urllib.error
import defusedxml.ElementTree as ET


# ニュースソース定義 (あとから追加可能)
# 各エントリ: {"name": 表示名, "url": RSSフィードURL, "max_items": 取得件数}
NEWS_FEEDS = [
    {
        "name": "GitHub Blog",
        "url": "https://github.blog/feed/",
        "max_items": 3,
    },
    # 追加例:
    # {
    #     "name": "Hacker News",
    #     "url": "https://hnrss.org/frontpage",
    #     "max_items": 3,
    # },
]

# リトライとキャッシュの設定
MAX_RETRIES = 3
RETRY_INITIAL_DELAY = 1  # 秒
RETRY_MAX_DELAY = 10  # 秒
RETRY_BACKOFF_MULTIPLIER = 2

# キャッシュの有効期限（秒） - デフォルト1時間
CACHE_TTL = 3600


class APIValidationError(Exception):
    """Exception raised when API response validation fails.
    
    This is a non-retryable error indicating the API returned
    a response in an unexpected format.
    """
    pass


def retry_with_backoff(max_retries=MAX_RETRIES, initial_delay=RETRY_INITIAL_DELAY,
                       max_delay=RETRY_MAX_DELAY, multiplier=RETRY_BACKOFF_MULTIPLIER):
    """Decorator to retry a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay between retries
        multiplier: Multiplier for exponential backoff

    Returns:
        Decorated function that retries on exception
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except APIValidationError:
                    # Don't retry API validation errors - they won't be fixed by retrying
                    raise
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"リトライ {attempt + 1}/{max_retries}: {func.__name__} - {e}")
                        time.sleep(delay)
                        delay = min(delay * multiplier, max_delay)
                    else:
                        print(f"最大リトライ回数に達しました: {func.__name__} - {e}")

            # 全てのリトライが失敗した場合、最後の例外を再送出
            raise last_exception

        return wrapper
    return decorator


def get_cache_path():
    """Get the path to the news cache file."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".news_cache.json")


def load_news_cache():
    """Load cached news items if they exist and are still valid.

    Returns:
        list of news articles or None if cache is invalid/expired
    """
    cache_path = get_cache_path()
    if not os.path.exists(cache_path):
        return None

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Check if timestamp exists
        if "timestamp" not in cache_data:
            print("キャッシュにタイムスタンプがありません")
            return None

        # Parse timestamp (may be timezone-aware or naive)
        cached_time = datetime.datetime.fromisoformat(cache_data["timestamp"])
        # Use timezone-naive datetime for consistency
        if cached_time.tzinfo is not None:
            cached_time = cached_time.replace(tzinfo=None)
        
        current_time = datetime.datetime.now()
        age_seconds = (current_time - cached_time).total_seconds()

        if age_seconds < CACHE_TTL:
            print(f"キャッシュからニュースを読み込みました (有効期限まで残り {int(CACHE_TTL - age_seconds)} 秒)")
            return cache_data.get("articles", [])
        else:
            print("キャッシュの有効期限が切れています")
            return None

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"キャッシュの読み込みに失敗: {e}")
        return None


def save_news_cache(articles):
    """Save news articles to cache.

    Args:
        articles: list of news articles to cache
    """
    cache_path = get_cache_path()
    cache_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "articles": articles
    }

    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"ニュースをキャッシュに保存しました ({len(articles)} 件)")
    except Exception as e:
        print(f"キャッシュの保存に失敗: {e}")


def load_spirit_data():
    """Load spirit data from .spirit.json"""
    spirit_file = '.spirit.json'
    if os.path.exists(spirit_file):
        with open(spirit_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle migration from old field names to new camelCase names
            if "last_utterance" in data:
                data["lastMessage"] = data.pop("last_utterance")
            if "last_updated" in data:
                data["lastUpdated"] = data.pop("last_updated")
            # Ensure profile exists
            if "profile" not in data:
                data["profile"] = {
                    "name": "Kaze-no-Kami",
                    "element": "wind",
                    "age": 231,
                    "personality": "gentle and wise"
                }
            return data
    else:
        # Default data
        return {
            "mood": "neutral",
            "lastMessage": "まだ何も語っていません…",
            "lastUpdated": datetime.datetime.now().isoformat() + "Z",
            "profile": {
                "name": "Kaze-no-Kami",
                "element": "wind",
                "age": 231,
                "personality": "gentle and wise"
            }
        }


def get_mood_based_on_time():
    """Determine mood based on current time"""
    hour = datetime.datetime.now().hour
    
    if 6 <= hour < 12:
        moods = ["cheerful", "energetic", "optimistic"]
    elif 12 <= hour < 18:
        moods = ["focused", "productive", "neutral"]
    elif 18 <= hour < 22:
        moods = ["relaxed", "contemplative", "peaceful"]
    else:
        moods = ["sleepy", "mysterious", "dreamy"]
    
    return random.choice(moods)


def get_latest_commit_message():
    """Get the latest commit message from git repository"""
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=format:%s'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def fetch_news(feeds=None, use_cache=True):
    """Fetch news from RSS feeds with caching and retry support.

    Args:
        feeds: list of feed dicts (default: NEWS_FEEDS).
               Each dict has 'name', 'url', and 'max_items'.
        use_cache: whether to use cached results if available (default: True)

    Returns:
        list of {"source": str, "title": str, "link": str}
    """
    # キャッシュから読み込みを試みる
    if use_cache:
        cached_articles = load_news_cache()
        if cached_articles is not None:
            return cached_articles

    if feeds is None:
        feeds = NEWS_FEEDS

    articles = []
    for feed in feeds:
        try:
            articles.extend(_fetch_single_feed_with_retry(feed))
        except Exception as e:
            # 個別のフィードのエラーはログに出力して続行
            print(f"フィード取得失敗 (全リトライ失敗): {feed.get('name', feed['url'])}")
            continue

    # 成功した場合のみキャッシュに保存
    if articles:
        save_news_cache(articles)

    return articles


@retry_with_backoff()
def _fetch_single_feed_with_retry(feed):
    """Fetch a single RSS feed with retry logic.

    Args:
        feed: dict with 'name', 'url', and 'max_items'

    Returns:
        list of articles from this feed

    Raises:
        Exception: if the fetch fails after all retries
    """
    articles = []
    req = urllib.request.Request(
        feed["url"],
        headers={"User-Agent": "CodeSpirits/1.0"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        xml_data = resp.read()

    root = ET.fromstring(xml_data)
    count = 0
    max_items = feed.get("max_items", 3)

    # First, try RSS 2.0 style <channel>/<item> elements.
    rss_items = root.findall(".//channel/item")
    if rss_items:
        for item in rss_items:
            title_el = item.find("title")
            link_el = item.find("link")
            if title_el is None or not title_el.text:
                continue
            articles.append({
                "source": feed["name"],
                "title": title_el.text.strip(),
                "link": link_el.text.strip() if link_el is not None and link_el.text else "",
            })
            count += 1
            if count >= max_items:
                break
    else:
        # Fallback: try Atom feed (<entry> elements in Atom namespace).
        atom_ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.findall(".//" + atom_ns + "entry"):
            title_el = entry.find(atom_ns + "title")
            if title_el is None or not title_el.text:
                continue

            # Prefer <link rel="alternate"> or a link without a rel attribute.
            link_el = None
            for candidate in entry.findall(atom_ns + "link"):
                rel = candidate.get("rel")
                if rel is None or rel == "alternate":
                    link_el = candidate
                    break

            link_href = ""
            if link_el is not None:
                href = link_el.get("href")
                if href:
                    link_href = href.strip()

            articles.append({
                "source": feed["name"],
                "title": title_el.text.strip(),
                "link": link_href,
            })
            count += 1
            if count >= max_items:
                break

    return articles


def get_mood_based_on_commit():
    """Determine mood based on latest commit message"""
    commit_message = get_latest_commit_message()
    if not commit_message:
        return None
    
    commit_message_lower = commit_message.lower()
    
    if 'fix' in commit_message_lower:
        return "calm"
    elif 'feat' in commit_message_lower:
        return "excited"
    
    return None


def get_utterance_for_mood(mood):
    """Get a random utterance based on mood"""
    utterances = {
        "cheerful": [
            "今日は素晴らしい一日になりそうです！",
            "コードが輝いて見えますね✨",
            "新しい発見がありそうな予感がします！"
        ],
        "energetic": [
            "さあ、今日も頑張りましょう！",
            "エネルギーが満ちています⚡",
            "何でもできそうな気分です！"
        ],
        "optimistic": [
            "きっと良いことが起こります",
            "希望に満ちた朝ですね",
            "前向きに進みましょう🌅"
        ],
        "focused": [
            "集中して取り組む時間です",
            "一つ一つ丁寧に進めていきましょう",
            "今こそ力を発揮する時です💪"
        ],
        "productive": [
            "効率よく作業が進んでいますね",
            "成果が見えてきました",
            "順調に前進しています📈"
        ],
        "neutral": [
            "穏やかな時間が流れています",
            "バランスの取れた状態です",
            "静かに見守っています👁️"
        ],
        "relaxed": [
            "リラックスした雰囲気ですね",
            "ゆったりとした時間を楽しみましょう",
            "心地よい夕暮れです🌅"
        ],
        "contemplative": [
            "深く考える時間ですね",
            "静寂の中に答えがあります",
            "哲学的な気分です🤔"
        ],
        "peaceful": [
            "平和な時間が流れています",
            "心が落ち着いています",
            "穏やかな夜です🌙"
        ],
        "sleepy": [
            "そろそろ休息の時間ですね...",
            "夢の世界へ誘われています😴",
            "静かな夜に包まれています"
        ],
        "mysterious": [
            "夜の神秘を感じます...",
            "秘密が眠る時間帯です🌙",
            "不思議な力が宿っています✨"
        ],
        "dreamy": [
            "夢のような時間ですね",
            "想像力が広がります💭",
            "幻想的な雰囲気です🌟"
        ],
        "calm": [
            "バグが消えて静けさが戻った。"
        ],
        "excited": [
            "新しい力が宿った！"
        ]
    }
    
    return random.choice(utterances.get(mood, ["何か感じるものがあります..."]))


def generate_news_comment(mood, profile, news_items):
    """Use GitHub Models API to generate a spirit-flavored news comment.

    Falls back to a simple static comment when the API is unavailable
    or GITHUB_TOKEN is not set.
    """
    if not news_items:
        return ""

    # フォールバック用の静的コメント
    fallback = "風に乗って届いたニュースをお届けします..."

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GitHub Models API: GITHUB_TOKEN が設定されていないため、フォールバックコメントを使用します")
        return fallback

    try:
        return _generate_news_comment_with_retry(mood, profile, news_items, token)
    except Exception as e:
        print(f"GitHub Models API の呼び出しに失敗 (全リトライ失敗): {e}")
        return fallback


@retry_with_backoff()
def _generate_news_comment_with_retry(mood, profile, news_items, token):
    """Internal function to call GitHub Models API with retry logic.

    Args:
        mood: current mood
        profile: spirit profile dict
        news_items: list of news articles
        token: GitHub token

    Returns:
        Generated comment string

    Raises:
        Exception: if the API call fails after all retries
    """
    name = profile.get("name", "精霊")
    element = profile.get("element", "wind")
    age = profile.get("age", "不明")
    personality = profile.get("personality", "gentle and wise")

    headlines = "\n".join(f"- {a['title']}" for a in news_items)
    user_prompt = (
        f"あなたは「{name}」という精霊です。"
        f"属性は{element}、年齢は{age}歳、"
        f"性格は「{personality}」です。\n"
        f"今の気分は「{mood}」です。\n\n"
        f"以下のニュース見出しについて、あなたのキャラクターらしく"
        f"短く（2〜3文で）コメントしてください:\n{headlines}"
    )

    body = json.dumps({
        "model": "openai/gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたはリポジトリに住む風の精霊です。"
                    "詩的で穏やかな口調で話します。"
                    "返答はコメント本文のみで、余計な前置きは不要です。"
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 200,
        "temperature": 0.8,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://models.github.ai/inference/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    choices = result.get("choices")
    if not choices:
        raise APIValidationError("GitHub Models API: レスポンスに choices がありません")

    content = choices[0].get("message", {}).get("content")
    if not content:
        raise APIValidationError("GitHub Models API: レスポンスに message.content がありません")

    return content.strip()


def _escape_md_link(text):
    """Escape markdown special characters in link text."""
    return text.replace("[", "\\[").replace("]", "\\]")


def update_readme(mood, utterance, news_items=None, news_comment=""):
    """Update all dynamic sections of README.md in a single read/write cycle."""
    readme_path = 'README.md'

    if not os.path.exists(readme_path):
        return

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # --- Spirit status ---
    status_pattern = r'(<!-- SPIRIT_STATUS_START -->)(.*?)(<!-- SPIRIT_STATUS_END -->)'
    new_status = f'<!-- SPIRIT_STATUS_START -->\n**気分**: {mood}\n<!-- SPIRIT_STATUS_END -->'
    content = re.sub(status_pattern, new_status, content, flags=re.DOTALL)

    # --- Spirit log ---
    log_pattern = r'(<!-- SPIRIT_LOG_START -->)(.*?)(<!-- SPIRIT_LOG_END -->)'
    new_log = f'<!-- SPIRIT_LOG_START -->\n> {utterance}\n<!-- SPIRIT_LOG_END -->'
    content = re.sub(log_pattern, new_log, content, flags=re.DOTALL)

    # --- News ---
    if news_items is None:
        news_items = []

    if news_items:
        lines = []
        if news_comment:
            for bq_line in news_comment.splitlines():
                lines.append(f"> {bq_line}" if bq_line.strip() else ">")
            lines.append("")
        for article in news_items:
            title = _escape_md_link(article['title'])
            link = article.get("link", "")
            # Escape parentheses in URLs to avoid breaking markdown links
            safe_link = link.replace("(", "%28").replace(")", "%29") if link else ""
            if safe_link:
                lines.append(f"- [{title}]({safe_link}) ({article['source']})")
            else:
                lines.append(f"- {title} ({article['source']})")
        news_body = "\n".join(lines)
    else:
        news_body = "> ニュースを取得できませんでした..."

    new_section = f"<!-- SPIRIT_NEWS_START -->\n{news_body}\n<!-- SPIRIT_NEWS_END -->"

    news_pattern = r'<!-- SPIRIT_NEWS_START -->.*?<!-- SPIRIT_NEWS_END -->'
    if re.search(news_pattern, content, flags=re.DOTALL):
        content = re.sub(news_pattern, new_section, content, flags=re.DOTALL)
    else:
        insert = f"\n## 精霊が届けるニュース\n\n{new_section}\n"
        # Prefer an explicit anchor comment if present, for robust placement.
        anchor_match = re.search(r'<!--\s*SPIRIT_NEWS_ANCHOR\s*-->', content)
        if anchor_match:
            start, end = anchor_match.span()
            content = content[:start] + insert + content[end:]
        else:
            sep_match = re.search(r'\n---\s*\n', content)
            if sep_match:
                pos = sep_match.start()
                content = content[:pos] + insert + content[pos:]
            else:
                content += insert

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)


def save_spirit_data(data):
    """Save spirit data to .spirit.json"""
    with open('.spirit.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    """Main function to update spirit status"""
    # Load current spirit data
    spirit_data = load_spirit_data()

    # Try to get mood based on commit first, then fall back to time-based
    new_mood = get_mood_based_on_commit()
    if new_mood is None:
        new_mood = get_mood_based_on_time()

    new_utterance = get_utterance_for_mood(new_mood)

    # Fetch news and generate AI comment
    news_items = fetch_news()
    news_comment = generate_news_comment(new_mood, spirit_data["profile"], news_items)

    # Update README first (single read/write for all sections)
    # If this fails, we don't want to save the spirit data
    try:
        update_readme(new_mood, new_utterance, news_items, news_comment)
    except Exception as e:
        print(f"エラー: READMEの更新に失敗しました: {e}", file=sys.stderr)
        raise

    # Only update spirit data if README update succeeded
    spirit_data['mood'] = new_mood
    spirit_data['lastMessage'] = new_utterance
    spirit_data['lastUpdated'] = datetime.datetime.now().isoformat() + "Z"
    spirit_data['news'] = news_items
    spirit_data['newsComment'] = news_comment

    # Save updated data
    try:
        save_spirit_data(spirit_data)
    except Exception as e:
        print(f"エラー: .spirit.jsonの保存に失敗しました: {e}", file=sys.stderr)
        # At this point README is updated but .spirit.json failed
        # We re-raise to signal failure, though README remains updated
        # The user will need to fix the underlying issue (e.g., permissions, disk space)
        raise

    print(f"精霊の状態を更新しました: {new_mood} - {new_utterance}")
    if news_items:
        print(f"ニュースを{len(news_items)}件取得しました")
    else:
        print("ニュースの取得をスキップしました")


if __name__ == "__main__":
    main()