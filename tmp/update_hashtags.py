import json
from pathlib import Path

# Load config
CONFIG_PATH = Path("w:/AntiGravity/SnapScrap_Local/stories/config/webapp_config_2.json")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Base hashtags
BASE_HASHTAGS = ["#Shorts", "#SaudiArabia", "#Dari", "#Saudi", "#Snapchat"]

for a in config.get('accounts', []):
    team = a.get('team', '')
    inf_name = a.get('influencer_name', '')
    username = a.get('username', '')
    
    parts = list(BASE_HASHTAGS)
    
    # 1. Add Personal Hashtag
    # Try to extract english name from old hashtags if it was there (e.g. 'Abu Omar #Falcons')
    old_tags = a.get('custom_hashtags') or a.get('hashtags') or ''
    eng_name = ""
    if old_tags and not old_tags.startswith('#'):
        eng_name = old_tags.split(' #')[0].strip()
        
    if eng_name and eng_name != old_tags:
        parts.insert(3, f"#{eng_name.replace(' ', '')}")
    elif inf_name:
        parts.insert(3, f"#{inf_name.replace(' ', '_')}")
    else:
        parts.insert(3, f"#{username.replace('.', '_')}")
        
    # 2. Add Team Hashtag
    if team and team != 'Other':
        parts.append(f"#{team.replace(' ', '')}")
        
    # Replace the list
    a['custom_hashtags'] = ' '.join(parts)

# Save
with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print('Successfully applied standard hashtags to all accounts.')
