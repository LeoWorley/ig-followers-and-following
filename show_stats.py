from database import Database, FollowerFollowing
from datetime import datetime
from sqlalchemy import desc

def show_followers_and_following():
    db = Database()
    
    # Get followers
    print("\n=== FOLLOWERS (Newest First) ===")
    followers = db.session.query(FollowerFollowing).filter(
        FollowerFollowing.is_follower == True,
        FollowerFollowing.is_lost == False
    ).order_by(desc(FollowerFollowing.added_at)).all()
    
    for follower in followers:
        added_date = follower.added_at.strftime('%Y-%m-%d %H:%M:%S')
        print(f"@{follower.follower_following_username} - Added: {added_date}")
    
    print(f"\nTotal Active Followers: {len(followers)}")
    
    # Get following
    print("\n=== FOLLOWING (Newest First) ===")
    following = db.session.query(FollowerFollowing).filter(
        FollowerFollowing.is_follower == False,
        FollowerFollowing.is_lost == False
    ).order_by(desc(FollowerFollowing.added_at)).all()
    
    for follow in following:
        added_date = follow.added_at.strftime('%Y-%m-%d %H:%M:%S')
        print(f"@{follow.follower_following_username} - Added: {added_date}")
    
    print(f"\nTotal Active Following: {len(following)}")

if __name__ == "__main__":
    show_followers_and_following()