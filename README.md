<p align="center">
  <img src="logo.png" alt="TrackMyClass Logo" width="400" height="400">
</p>

# TrackMyClass Application

> A lightweight Discord front-end for TrackMyClass — never miss an ASU class opening again.

This repository contains only the **Discord bot** that connects to a private backend API. It does **not** include the server or data-storage code. For full program details, visit [trackmyclass.org](https://trackmyclass.org).

---

## 🤖 Features

- **Real-time alerts**  
  Notifies you within **1 minute** when seats open or fill in any tracked class.  
- **Unlimited subscriptions**  
  Track as many courses as you like—no extra fees.
- **Open-Seat History**  
  View the last 5 open/close events and average open duration.  
- **Overload insights**  
  Get “overload” status and recent seat-change history for any class.  
- **DM interactions**  
  Notifies user of open classes in DMs for privacy and clarity.

---

## 💬 Slash Commands & Usage

All commands must be sent in **Direct Messages** to the bot.

| Command                   | Description                                                                                     |
|---------------------------|-------------------------------------------------------------------------------------------------|
| `/start`                  | Register your Discord account so TrackMyClass can DM you alerts.                                 |
| `/subscribe <class_number>` | Watch a class (e.g. `/subscribe 12345`). You’ll be notified when seats open or fill.          |
| `/unsubscribe <class_number>` | Stop alerts for a class (e.g. `/unsubscribe 12345`).                                        |
| `/subscriptions`          | List all classes you’re tracking and their current seat counts.                                  |
| `/xray <class_number>`    | Get “overload” insights and recent seat adjustments (e.g. `/xray 12345`).                       |
| `/history <class_number>` | Show the last 5 open/close events and average open duration (e.g. `/history 12345`).            |
| `/testdm`                 | Verify that the bot can send you DMs. If it fails, adjust your Discord privacy settings.        |

> **Note:** If you try the /subscribe command in a server channel, you’ll receive a “DM Only” error—commands must be issued via DM.

---

## 🔒 Environment Variables

| Variable         | Description                                                                                      |
|------------------|--------------------------------------------------------------------------------------------------|
| `FLASK_API_URL`  | URL of the private backend API (e.g. `https://api.trackmyclass.org`).                             |
| `DISCORD_TOKEN`  | Your Discord bot token (keep this secret!).                                                     |
| `GUILD_ID`       | (Optional) Guild ID for testing slash-command sync.                                              |

---

## 🤝 Contributing

This repo is for the **bot only**. The backend lives in a private repository. If you’d like to contribute:

1. Fork this repo and open a PR.  
2. Ensure you do **not** include any backend code or secrets.  
3. Follow the existing code style and add tests for any new commands.

---

## 📄 License

Distributed under the [GNU General Public License v3.0](LICENSE). Feel free to use and modify!
