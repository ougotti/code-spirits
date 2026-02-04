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
import subprocess
import urllib.request
import xml.etree.ElementTree as ET


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


def fetch_news(feeds=None):
    """Fetch news from RSS feeds.

    Args:
        feeds: list of feed dicts (default: NEWS_FEEDS).
               Each dict has 'name', 'url', and 'max_items'.

    Returns:
        list of {"source": str, "title": str, "link": str}
    """
    if feeds is None:
        feeds = NEWS_FEEDS

    articles = []
    for feed in feeds:
        try:
            req = urllib.request.Request(
                feed["url"],
                headers={"User-Agent": "CodeSpirits/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read()

            root = ET.fromstring(xml_data)
            count = 0
            max_items = feed.get("max_items", 3)

            # First, try RSS 2.0 style <item> elements.
            rss_items = list(root.iter("item"))
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
        except Exception:
            continue

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
        return fallback

    headlines = "\n".join(f"- {a['title']}" for a in news_items)
    user_prompt = (
        f"あなたは「{profile['name']}」という精霊です。"
        f"属性は{profile['element']}、年齢は{profile['age']}歳、"
        f"性格は「{profile['personality']}」です。\n"
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
        "temperature": 0.9,
    }).encode("utf-8")

    try:
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
            result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"].strip()
    except Exception:
        return fallback


def update_readme(mood, utterance):
    """Update README.md with new spirit status and utterance"""
    readme_path = 'README.md'
    
    if not os.path.exists(readme_path):
        return
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update spirit status
    status_pattern = r'(<!-- SPIRIT_STATUS_START -->)(.*?)(<!-- SPIRIT_STATUS_END -->)'
    new_status = f'<!-- SPIRIT_STATUS_START -->\n**気分**: {mood}\n<!-- SPIRIT_STATUS_END -->'
    content = re.sub(status_pattern, new_status, content, flags=re.DOTALL)
    
    # Update spirit log
    log_pattern = r'(<!-- SPIRIT_LOG_START -->)(.*?)(<!-- SPIRIT_LOG_END -->)'
    new_log = f'<!-- SPIRIT_LOG_START -->\n> {utterance}\n<!-- SPIRIT_LOG_END -->'
    content = re.sub(log_pattern, new_log, content, flags=re.DOTALL)
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_readme_news(news_items, news_comment):
    """Update README.md with the news section."""
    readme_path = 'README.md'
    if not os.path.exists(readme_path):
        return

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # ニュースコンテンツを構築
    if news_items:
        lines = []
        if news_comment:
            lines.append(f"> {news_comment}")
            lines.append("")
        for article in news_items:
            if article.get("link"):
                lines.append(f"- [{article['title']}]({article['link']}) ({article['source']})")
            else:
                lines.append(f"- {article['title']} ({article['source']})")
        news_body = "\n".join(lines)
    else:
        news_body = "> ニュースを取得できませんでした..."

    new_section = f"<!-- SPIRIT_NEWS_START -->\n{news_body}\n<!-- SPIRIT_NEWS_END -->"

    # マーカーが既にあれば置換、なければ --- の前に挿入
    news_pattern = r'<!-- SPIRIT_NEWS_START -->.*?<!-- SPIRIT_NEWS_END -->'
    if re.search(news_pattern, content, flags=re.DOTALL):
        content = re.sub(news_pattern, new_section, content, flags=re.DOTALL)
    else:
        sep = content.find('\n---\n')
        insert = f"\n## 精霊が届けるニュース\n\n{new_section}\n"
        if sep != -1:
            content = content[:sep] + insert + content[sep:]
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

    # Update spirit data
    spirit_data['mood'] = new_mood
    spirit_data['lastMessage'] = new_utterance
    spirit_data['lastUpdated'] = datetime.datetime.now().isoformat() + "Z"
    spirit_data['news'] = news_items
    spirit_data['newsComment'] = news_comment

    # Save updated data
    save_spirit_data(spirit_data)

    # Update README
    update_readme(new_mood, new_utterance)
    update_readme_news(news_items, news_comment)

    print(f"精霊の状態を更新しました: {new_mood} - {new_utterance}")
    if news_items:
        print(f"ニュースを{len(news_items)}件取得しました")
    else:
        print("ニュースの取得をスキップしました")


if __name__ == "__main__":
    main()