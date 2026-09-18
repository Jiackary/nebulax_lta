from datetime import datetime
from app.config import HOME_DEFAULT, SGT
from app.services import planner
from datetime import timedelta
d = datetime.now(SGT).date()+timedelta(days=1)
while d.weekday()>4: d+=timedelta(days=1)
for ps in (False, True):
    p = planner.plan_trip(HOME_DEFAULT, datetime(d.year,d.month,d.day,10,30,tzinfo=SGT), prefer_sheltered=ps)
    s = p["summary"]
    print(ps, {k:s.get(k) for k in ("leave_by","range_min","buffer_min","arrival_window")})
