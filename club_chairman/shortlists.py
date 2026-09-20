"""Private recruitment lists; stable player links, no simulation side effects."""
from copy import deepcopy

MAX_LISTS = 20
MAX_NAME = 32


def initialise(s):
    plan=s['planning']
    plan['shortlists']=dict(active='list-0',next_id=1,items=[
        dict(id='list-0',name='Shortlist',players=list(plan['shortlist']))])


def active(plan):
    data=plan['shortlists']
    return next(item for item in data['items'] if item['id']==data['active'])


def validate_data(data,known):
    from .simulation import require
    require(isinstance(data,dict),'Invalid shortlist collection.')
    items=data.get('items')
    require(isinstance(items,list) and 1<=len(items)<=MAX_LISTS,'Keep between one and twenty shortlists.')
    ids=[];names=[]
    for item in items:
        require(isinstance(item,dict),'Invalid shortlist record.')
        sid=item.get('id');name=item.get('name');players=item.get('players')
        require(isinstance(sid,str) and sid.startswith('list-') and sid[5:].isascii() and sid[5:].isdigit(),'Invalid shortlist identity.')
        require(isinstance(name,str) and name==name.strip() and 1<=len(name)<=MAX_NAME and name.isprintable(),'Use a shortlist name of 1–32 printable characters.')
        require(isinstance(players,list) and all(isinstance(pid,str) for pid in players),'Invalid shortlist members.')
        require(len(players)==len(set(players)) and set(players)<=known,'Shortlists must contain unique known players.')
        ids.append(sid);names.append(name.casefold())
    require(len(ids)==len(set(ids)) and len(names)==len(set(names)),'Shortlist names and identities must be unique.')
    require(data.get('active') in ids,'Select an existing shortlist.')
    require(type(data.get('next_id')) is int and data['next_id']>max(int(sid[5:]) for sid in ids),'Invalid next shortlist identity.')


def restore(s,data):
    validate_data(data,{p['id'] for p in s['players']})
    s['planning']['shortlists']=deepcopy(data)
    s['planning']['shortlist']=list(active(s['planning'])['players'])


def apply(s,payload):
    from .simulation import require
    plan=s['planning'];data=deepcopy(plan['shortlists']);op=payload.get('operation')
    require(op in ('create','rename','select','delete'),'Unknown shortlist operation.')
    item=next((i for i in data['items'] if i['id']==payload.get('id')),None)
    if op!='create':require(item is not None,'That shortlist no longer exists.')
    if op=='create':
        item=dict(id=f"list-{data['next_id']}",name=payload.get('name'),players=[])
        data['next_id']+=1;data['items'].append(item);data['active']=item['id']
    elif op=='rename':item['name']=payload.get('name')
    elif op=='select':data['active']=item['id']
    else:
        require(len(data['items'])>1,'Keep at least one shortlist.')
        data['items'].remove(item)
        if data['active']==item['id']:data['active']=data['items'][0]['id']
    restore(s,data)
    verb=dict(create='Created',rename='Renamed',select='Selected',delete='Deleted')[op]
    return f"{verb} shortlist: {item['name']}. Time and money are unchanged."


def validate(s):
    plan=s['planning'];validate_data(plan.get('shortlists'),{p['id'] for p in s['players']})
    from .simulation import require
    require(plan['shortlist']==active(plan)['players'],'Active shortlist membership is inconsistent.')
