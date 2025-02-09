# Instagram Follower/Following Tracker

This project tracks daily changes in Instagram followers and following lists for a specified account. It maintains historical data and generates daily reports of changes.

## Features

- Daily monitoring of followers and following lists
- Tracks new followers and unfollowers
- Tracks new and removed following accounts
- Historical data storage
- Daily change reports
- View followers/following lists sorted by date added

## Setup

You can run this project either using a virtual environment or Docker.

### Option 1: Virtual Environment

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

### Option 2: Docker

1. Create a `.env` file with your Instagram credentials (same as above).

2. Build the Docker image:
```bash
docker build -t instagram-tracker .
```

3. Run the tracker in Docker:
```bash
docker run -it \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/instagram_cookies.json:/app/instagram_cookies.json \
  -v $(pwd)/instagram_tracker.db:/app/instagram_tracker.db \
  instagram-tracker
```

To run in background mode, add the `-d` flag:
```bash
docker run -d \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/instagram_cookies.json:/app/instagram_cookies.json \
  -v $(pwd)/instagram_tracker.db:/app/instagram_tracker.db \
  instagram-tracker
```

To view logs when running in background:
```bash
docker ps  # get the container ID
docker logs -f <container-id>
```

## Viewing Statistics

You can view your followers and following lists sorted by date added using the `show_stats.py` script:

### Using Virtual Environment:
```bash
python show_stats.py
```

### Using Docker:
```bash
docker run -it \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/instagram_tracker.db:/app/instagram_tracker.db \
  instagram-tracker python show_stats.py
```

This will display:
- All current followers, sorted by newest first
- Total number of followers
- All accounts you're following, sorted by newest first
- Total number of accounts you're following

## Configuration

The tracker runs daily at a specified time. You can modify the schedule in `main.py`.

## Data Storage

All data is stored in a SQLite database (`instagram_tracker.db`) with the following information:
- Daily follower snapshots
- Daily following snapshots
- Change logs

## Security Note

Please keep your `.env` file secure and never commit it to version control.

## License

This project is licensed under the [MIT License](LICENSE).
