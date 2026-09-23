from datetime import datetime, timedelta

def build_batch_schedule(start_at: datetime) -> list[datetime]:
    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise ValueError("start_at must include a timezone")

    return [
        start_at + timedelta(hours=hour)
        for hour in range(0, 24, 3) 
    ]