# Instagram Follower/Following Tracker

This project tracks daily changes in Instagram followers and following lists for a specified account. It maintains historical data and generates daily reports of changes.

## Features

- Daily monitoring of followers and following lists
- Tracks new followers and unfollowers
- Tracks new and removed following accounts
- Historical data storage
- Daily change reports

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
.\venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Instagram credentials:
```
IG_USERNAME=your_username
IG_PASSWORD=your_password
TARGET_ACCOUNT=account_to_track
```

4. Run the tracker:
```bash
python main.py
```

## Configuration

The tracker runs daily at a specified time. You can modify the schedule in `main.py`.

## Data Storage

All data is stored in a SQLite database (`instagram_tracker.db`) with the following information:
- Daily follower snapshots
- Daily following snapshots
- Change logs

## Security Note

Please keep your `.env` file secure and never commit it to version control.
