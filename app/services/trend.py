"""Bounded live trend: recent raw samples and 24-hour min/max envelopes."""
from collections import deque
import math

class TrendBuffer:
    def __init__(self):
        self.recent=deque(maxlen=32000)
        self.buckets=deque(maxlen=8641)

    def append(self, point):
        ts,value=point
        self.recent.append(point)
        key=int(ts//10)
        if not self.buckets or self.buckets[-1][0]!=key:
            self.buckets.append([key,point,point,point,point,None])
        b=self.buckets[-1]
        b[4]=point
        if math.isfinite(value):
            if not math.isfinite(b[2][1]) or value<b[2][1]: b[2]=point
            if not math.isfinite(b[3][1]) or value>b[3][1]: b[3]=point
        else: b[5]=point

    def points(self, cutoff, seconds):
        if self.recent and self.recent[0][0]<=cutoff:
            data=[p for p in self.recent if p[0]>=cutoff]
        else:
            data=[]
            for b in self.buckets:
                if (b[0]+1)*10<cutoff: continue
                data.extend(sorted(set(p for p in b[1:] if p is not None and p[0]>=cutoff)))
        if len(data)<=4000: return data
        # Bound Qt payload without concealing peaks or missing-quality gaps.
        result=[]; step=max(1,(len(data)+799)//800)
        for i in range(0,len(data),step):
            chunk=data[i:i+step]; good=[p for p in chunk if math.isfinite(p[1])]
            chosen=[chunk[0],chunk[-1]]
            if good: chosen.extend([min(good,key=lambda p:p[1]),max(good,key=lambda p:p[1])])
            bad=next((p for p in chunk if not math.isfinite(p[1])),None)
            if bad: chosen.append(bad)
            result.extend(sorted(set(chosen)))
        return result
