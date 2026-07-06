# Safith Flight Bot 🛫

> **Free flight price alerts via Telegram. Compare multiple airlines. Get smart recommendations.**

[![GitHub Stars](https://img.shields.io/github/stars/safith001/flight-bot?style=social)](https://github.com/safith001/flight-bot)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)

---

## ✨ Features

- ✅ Monitors **7 airlines** simultaneously
- ✅ Tracks **6 major flight routes**
- ✅ Checks prices **every 6 hours**
- ✅ **Claude AI-powered** smart recommendations
- ✅ **100% Free** - No signup, no payments
- ✅ **Telegram alerts** - Direct to your phone
- ✅ **24/7 monitoring** - Runs automatically
- ✅ **99.9% uptime** - Never crashes

---

## 🔄 How It Works

### Every 6 Hours:

```
1. Fetch flight prices from 7 airlines
   ↓
2. Claude AI analyzes all options
   ↓
3. Picks top 3 best deals
   ↓
4. Sends smart recommendation to Telegram
```

### Example Alert:

```
✈️ FLIGHT PRICE ALERT
Check: 2026-06-11 18:00:00
════════════════════════════════════════

3. CMB TO CHENNAI
────────────────────────────────────────
Status: 🔴 RED
Price: RM571
Airline: IndiGo
Duration: 1 hr 20 min
Book: https://www.google.com/flights?...
```

### Alert Types:

- 🔴 **RED** - Price below budget (instant alert)
- 🟡 **YELLOW** - Within 10% of budget (instant alert)
- ⚫ **SILENT** - Above budget (no message)

---

## 🚀 Quick Start

### For Users

1. Open **Telegram**
2. Search for **@safith_flights_bot**
3. Click **Start**
4. Receive flight price alerts automatically

No signup. No payment. Just alerts.

---

## 🔧 For Developers

### Prerequisites

- Python 3.10+
- Telegram Bot Token
- Claude API Key
- Airline API credentials

### Installation

```bash
# Clone repository
git clone https://github.com/safith001/flight-bot.git
cd flight-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your tokens

# Run locally
python flight_bot.py
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Telegram
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Claude AI
CLAUDE_API_KEY=your_claude_key

# Airlines
SRILANKAN_API_KEY=your_key
INDIGO_API_KEY=your_key
```

### Flight Routes

Edit to customize routes:

```python
ROUTES = [
    {"from": "KUL", "to": "CMB", "name": "KL to CMB"},
    {"from": "CMB", "to": "KUL", "name": "CMB to KL"},
    {"from": "CMB", "to": "MAA", "name": "CMB to Chennai"},
    # Add more routes...
]

BUDGETS = {
    "KL to CMB": 700,
    "CMB to KL": 700,
    # Set your budget for each route...
}
```

---

## 💻 Technology Stack

- **Python 3.10** - Core language
- **Telegram Bot API** - Notifications
- **Claude AI** - Intelligence & recommendations
- **GitHub Actions** - 24/7 automation
- **PostgreSQL** - Data storage (optional)

---

## 📁 Project Structure

```
flight-bot/
├── flight_bot.py              # Main bot
├── requirements.txt           # Dependencies
├── .env.example              # Config template
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── daily_prices.json         # Price history
│
└── .github/
    └── workflows/
        └── flight-bot.yml    # GitHub Actions schedule
```

---

## 🤝 Contributing

We welcome contributions!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a Pull Request

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file

---

## 🐛 Troubleshooting

### Bot Not Sending Messages
- Check `TELEGRAM_TOKEN` in .env
- Verify `TELEGRAM_CHAT_ID` is correct
- Check GitHub Actions logs

### Prices Not Updating
- Verify airline API credentials
- Check rate limiting from APIs
- Review logs for errors

### Claude Errors
- Verify `CLAUDE_API_KEY` is correct
- Check API quota
- Review error messages

---

## 📊 Quick Facts

| Metric | Value |
|--------|-------|
| Airlines Monitored | 7 |
| Flight Routes | 6 |
| Check Frequency | Every 6 hours |
| Uptime Target | 99.9% |
| Cost | Free |

---

## 📞 Support

- Open an **issue** on GitHub for bugs
- Submit **pull requests** for improvements
- Check **logs** for troubleshooting

---

## 🙏 Acknowledgments

- **Anthropic** - Claude AI
- **Telegram** - Bot platform
- **GitHub** - Free hosting & Actions
- Open source community

---

**Made with ❤️ by Safith**

Simple. Fast. Free. 🚀
