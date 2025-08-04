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
    
    # Update spirit data
    spirit_data['mood'] = new_mood
    spirit_data['lastMessage'] = new_utterance
    spirit_data['lastUpdated'] = datetime.datetime.now().isoformat() + "Z"
    
    # Save updated data
    save_spirit_data(spirit_data)
    
    # Update README
    update_readme(new_mood, new_utterance)
    
    print(f"精霊の状態を更新しました: {new_mood} - {new_utterance}")


if __name__ == "__main__":
    main()