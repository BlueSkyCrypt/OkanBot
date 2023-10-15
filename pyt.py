from datetime import datetime
from zoneinfo import ZoneInfo

jst = ZoneInfo("Asia/Tokyo")

def datetimenow():
    aware_jst = datetime.now(jst)
    return aware_jst.replace(tzinfo=None)
