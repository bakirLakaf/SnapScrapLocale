import json
import os
from pathlib import Path

# Configuration
# Use user_id 2 since the active user in the dashboard is user_id=2
CONFIG_PATH = Path("stories/config/webapp_config_2.json")
BASE_DIR = Path(r"w:\AntiGravity\SnapScrap_Local")
CONFIG_FILE = BASE_DIR / "stories" / "config" / "webapp_config_2.json"

# Data for Teams
TEAMS_DATA = {
    "Falcons": {
        "hashtags": "#السعودية #فالكونز #Falcons",
        "members": [
            {"username": "abo3abd-f16", "name": "أبو عمر", "slug": "Abu Omar"},
            {"username": "abo_sa3ad", "name": "أبو السعد", "slug": "Abu Al-Saad"},
            {"username": "fawaz_707", "name": "فواز", "slug": "Fawaz"},
            {"username": "mohammed_oden", "name": "أودين", "slug": "Odin"},
            {"username": "opiilz", "name": "أوبلز", "slug": "Obles"},
            {"username": "drb7h", "name": "دربحه", "slug": "Drb7ah"},
            {"username": "abuabeer", "name": "أبو عبير", "slug": "Abu Abeer"},
            {"username": "azizsamily", "name": "عزيز", "slug": "Aziz"},
            {"username": "banderitax", "name": "بندريتا", "slug": "Banderitax"},
            {"username": "raed", "name": "رائد", "slug": "Raed"},
            {"username": "lily", "name": "للي", "slug": "Lily"},
            {"username": "adel", "name": "عادل", "slug": "Adel"},
            {"username": "amer", "name": "عامر", "slug": "Amer"},
            {"username": "mexic", "name": "مكسيكي", "slug": "Mexic"},
            {"username": "slo7", "name": "صليح", "slug": "Slo7"},
            {"username": "hamada", "name": "حمادة", "slug": "Hamada"},
            {"username": "falconsesports", "name": "فالكونز الرسمي", "slug": "Falcons Official"}
        ]
    },
    "POWER": {
        "hashtags": "#باور #السعودية #POWER",
        "members": [
            {"username": "shongxbong_yt", "name": "شونق", "slug": "Shong"},
            {"username": "bnouh111", "name": "أبو نوح", "slug": "Abu Nouh"},
            {"username": "yznsaa1", "name": "يزن", "slug": "Yazan"},
            {"username": "d7oomysnap", "name": "دحومي", "slug": "D7oomy"},
            {"username": "mrfifasa", "name": "مستر فيفا", "slug": "Mr FIFA"},
            {"username": "abuswe7l", "name": "أبوسويحل", "slug": "Abu Swehl"},
            {"username": "iiklo25", "name": "خلودي 25", "slug": "Khloudi"},
            {"username": "mjrmgems", "name": "مجرم قيمز", "slug": "MjrmGames"},
            {"username": "ibralomry", "name": "أبوخليل", "slug": "Abu Khalil"},
            {"username": "iirakan", "name": "راكان", "slug": "Rakan"},
            {"username": "irayan_gh", "name": "ريان", "slug": "Rayan"},
            {"username": "powr_rob", "name": "روب", "slug": "Rob"},
            {"username": "fares_fu", "name": "فارس", "slug": "Fares"},
            {"username": "i3zoooz29", "name": "كمستكا", "slug": "Kmistka"},
            {"username": "virussyyy", "name": "فايروس", "slug": "Virus"},
            {"username": "glory19mu", "name": "جلوري", "slug": "Glory"},
            {"username": "ffearfful", "name": "فيرفول", "slug": "FearFull"},
            {"username": "ieaglee", "name": "إيغل", "slug": "Eagle"},
            {"username": "tehazm", "name": "عبدالله أزم", "slug": "tehazm"},
            {"username": "shxwm", "name": "أسامه", "slug": "Osama"},
            {"username": "jaservii", "name": "جاسر", "slug": "Jaser"},
            {"username": "powrnedal", "name": "نضال", "slug": "Nedal"},
            {"username": "ahmedowsari", "name": "أحمد شو", "slug": "AhmedShow"},
            {"username": "ecnnu", "name": "يزيد", "slug": "Yazeed"},
            {"username": "zeeyadx", "name": "زياد إكس", "slug": "ZiadX"},
            {"username": "poweresports", "name": "باور الرسمي", "slug": "POWER Official"}
        ]
    },
    "TU": {
        "hashtags": "#توبز #السعودية #TU",
        "members": [
            {"username": "snap.topz", "name": "توبز", "slug": "Topz"}
        ]
    },
    "Twisted Minds": {
        "hashtags": "#TwistedMinds #السعودية",
        "members": [
            {"username": "TwisMinds", "name": "TwisMinds Official", "slug": "TwisMinds"}
        ]
    },
    "R8": {
        "hashtags": "#R8 #السعودية",
        "members": [
            {"username": "r8esports", "name": "R8 Official", "slug": "R8"}
        ]
    },
    "PEAKS": {
        "hashtags": "#PEAKS #السعودية",
        "members": [
            {"username": "peaksgg", "name": "PEAKS Official", "slug": "PEAKS"}
        ]
    },
    "LYNX": {
        "hashtags": "#LYNX #السعودية",
        "members": [
            {"username": "lynxesports", "name": "LYNX Official", "slug": "LYNX"}
        ]
    },
    "Bitbot": {
        "hashtags": "#Bitbot #السعودية",
        "members": [
            {"username": "bitbot_sa", "name": "Bitbot Official", "slug": "Bitbot"}
        ]
    }
}

def main():
    if not CONFIG_FILE.exists():
        print(f"Error: {CONFIG_FILE} not found")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    accounts = config.get("accounts", [])
    account_map = {a["username"].lower(): a for a in accounts}

    # Add/Update members
    for team_name, team_info in TEAMS_DATA.items():
        for member in team_info["members"]:
            username_lower = member["username"].lower()
            if username_lower in account_map:
                # Update existing
                acc = account_map[username_lower]
                acc["team"] = team_name
                acc["influencer_name"] = member["name"]
                acc["hashtags"] = f"{member['slug']} #{team_name}"
            else:
                # Add new
                new_acc = {
                    "username": member["username"],
                    "checked": True,
                    "avatar": None,
                    "team": team_name,
                    "influencer_name": member["name"],
                    "hashtags": f"{member['slug']} #{team_name}"
                }
                accounts.append(new_acc)
                account_map[username_lower] = new_acc

    # Add teams_config
    teams_config = config.get("teams_config", {})
    for team_name, team_info in TEAMS_DATA.items():
        teams_config[team_name] = {"hashtags": team_info["hashtags"]}
    config["teams_config"] = teams_config

    # Save
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"Successfully seeded {len(accounts)} accounts across {len(TEAMS_DATA)} teams.")

if __name__ == "__main__":
    main()
