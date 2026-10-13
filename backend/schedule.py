from datetime import datetime, timedelta
import math
from .security import LOCAL_TZ


def iso(value):
    return value.astimezone(__import__('datetime').timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')


def medication_schedule(records, start, end):
    begin = datetime.fromisoformat(start + 'T00:00:00').replace(tzinfo=LOCAL_TZ)
    finish_period = datetime.fromisoformat(end + 'T23:59:59').replace(tzinfo=LOCAL_TZ)
    out = []
    applications = {(r['treatment_id'],r['data'].get('scheduledAt')):r for r in records if r['kind']=='application'}
    for t in (r for r in records if r['kind']=='treatment'):
        d = t['data']; interval = d.get('intervalHours')
        if not interval or not d.get('time'):
            continue
        origin = datetime.fromisoformat(d['date']+'T'+d['time']).replace(tzinfo=LOCAL_TZ)
        finish = finish_period
        if d.get('endDate'):
            finish = min(finish,datetime.fromisoformat(d['endDate']+'T23:59:59').replace(tzinfo=LOCAL_TZ))
        for c in records:
            if c['kind']=='completion' and c['treatment_id']==t['id']:
                cutoff = datetime.fromisoformat(c['data']['date']+'T'+(c['data'].get('time') or '00:00')).replace(tzinfo=LOCAL_TZ)
                finish = min(finish,cutoff-timedelta(milliseconds=1))
        step = timedelta(hours=interval)
        time = origin + max(0,math.ceil((begin-origin)/step)) * step
        while time <= finish and len(out)<5000:
            stamp = iso(time); applied = applications.get((t['id'],stamp))
            out.append({'treatmentId':t['id'],'catId':t['cat_id'],'label':d['label'],'dose':d['dose'],
                        'date':time.strftime('%Y-%m-%d'),'time':time.strftime('%H:%M'),'scheduledAt':stamp,
                        'applied':bool(applied),'responsible':applied.get('responsible','') if applied else ''})
            time += step
    return sorted(out,key=lambda x:x['scheduledAt'])


def unscheduled(records):
    closed = {r['treatment_id'] for r in records if r['kind']=='completion'}
    return sum(r['kind']=='treatment' and not r['data'].get('intervalHours') and r['id'] not in closed for r in records)
