from app.services.trend import TrendBuffer
from app.storage import Repository
from app.models import Sample, Device

def test_day_retains_start_end_and_peak_with_bounded_output():
    b=TrendBuffer()
    for i in range(86401): b.append((i,9999 if i==11 else i%10))
    points=b.points(0,86400)
    assert points[0][0]==0 and points[-1][0]==86400
    assert max(p[1] for p in points)==9999
    assert len(points)<=4000
    assert len(b.recent)<=32000 and len(b.buckets)<=8641

def test_month_overview_includes_older_than_20000(tmp_path):
    r=Repository(tmp_path/'test.db')
    r.append([Sample(i*100,'tag','device',999 if i==1 else 1,'OK') for i in range(25001)])
    result=r.history_overview(['tag'],0,31*86400)
    assert result['total']==25001
    assert min(p['ts'] for p in result['rows'])==0
    assert max(p['value'] for p in result['rows'])==999
    assert len(result['rows'])<=2402
    assert len(result['recent'])==500
    r.close()

def test_fast_interval_validation():
    Device(interval_ms=20).validate()
