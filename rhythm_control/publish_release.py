# coding: utf-8
"""Run by GitHub Actions after configuring this repository. Never called by app/build tools."""
import hashlib,json,os,re,sys,urllib.request,urllib.error
from pathlib import Path

REPO='cofearis/claude-todo'
PREFIX='rhythm_control-v'
ASSET='rhythm-update.json'
TAG=re.compile(r'^rhythm_control-v(\d+)\.(\d+)\.(\d+)$')
def owned_release(release):
    names={a['name'] for a in release.get('assets',[])}
    match=TAG.fullmatch(release.get('tag_name',''))
    return bool(match and not release.get('draft') and not release.get('prerelease') and ASSET in names and
                'rhythm_control_'+'.'.join(match.groups())+'.apk' in names)
def prune_candidates(releases,keep=5):
    scoped=[r for r in releases if owned_release(r)]
    scoped.sort(key=lambda r:tuple(int(n) for n in TAG.fullmatch(r['tag_name']).groups()),reverse=True)
    return scoped[keep:]
def validate(data,apk):
    assert data['schema']==1 and data['packageName']=='cn.rhythm.control'
    assert re.fullmatch(r'\d+\.\d+\.\d+',data['versionName']) and isinstance(data['versionCode'],int) and data['versionCode']>0
    assert apk.name=='rhythm_control_'+data['versionName']+'.apk'
    assert data['apkUrl']==f'https://github.com/{REPO}/releases/download/{PREFIX}{data["versionName"]}/{apk.name}'
    assert 0<data['size']<=64*1024*1024 and apk.stat().st_size==data['size']
    assert hashlib.sha256(apk.read_bytes()).hexdigest()==data['sha256']
class GitHub:
    def __init__(self,token):self.token=token
    def call(self,path,method='GET',data=None,binary=None,content_type='application/json'):
        url=path if path.startswith('https://') else f'https://api.github.com/repos/{REPO}{path}'
        if not (url.startswith(f'https://api.github.com/repos/{REPO}/') or url.startswith(f'https://uploads.github.com/repos/{REPO}/')):raise ValueError('Unexpected API target')
        body=binary if binary is not None else (json.dumps(data).encode() if data is not None else None)
        request=urllib.request.Request(url,data=body,method=method,headers={
            'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json',
            'X-GitHub-Api-Version':'2022-11-28','User-Agent':'RhythmRelease','Content-Type':content_type})
        with urllib.request.urlopen(request,timeout=60) as response:
            raw=response.read();return json.loads(raw) if raw else None
    def releases(self):
        result=[]
        for page in range(1,101):
            batch=self.call(f'/releases?per_page=100&page={page}');result+=batch
            if len(batch)<100:return result
        raise RuntimeError('Too many release pages; cleanup aborted')
    def manifest(self,release):
        url=f'https://github.com/{REPO}/releases/download/{release["tag_name"]}/{ASSET}'
        with urllib.request.urlopen(url,timeout=30) as response:
            data=response.read(65537)
        if len(data)>65536:raise RuntimeError('Release manifest too large')
        return json.loads(data)
def publish(api,data,apk,commit):
    tag=PREFIX+data['versionName'];existing=api.releases()
    matches=[r for r in existing if r.get('tag_name')==tag]
    if matches and not matches[0].get('draft'):
        # Retry cleanup after a failed run without replacing any published binary.
        if not owned_release(matches[0]) or api.manifest(matches[0])!=data:raise RuntimeError('Version already exists with different contents')
        for release in prune_candidates(existing):api.call('/releases/'+str(release['id']),'DELETE')
        print('Existing identical release verified; retention complete');return
    if matches:raise RuntimeError('A draft already exists; inspect it before retrying')
    newest=max((tuple(int(n) for n in TAG.fullmatch(r['tag_name']).groups()) for r in existing if owned_release(r)),default=(-1,-1,-1))
    if tuple(map(int,data['versionName'].split('.')))<=newest:raise RuntimeError('Refusing an older version')
    if newest!=(-1,-1,-1):
        previous=next(r for r in existing if owned_release(r) and tuple(map(int,TAG.fullmatch(r['tag_name']).groups()))==newest)
        if data['versionCode']<=int(api.manifest(previous)['versionCode']):raise RuntimeError('versionCode must increase')
    # Only a completely uploaded and verified draft may become visible to the app.
    draft=api.call('/releases','POST',{'tag_name':tag,'target_commitish':commit,'name':'节律控制 '+data['versionName'],
        'body':'节律控制 Android '+data['versionName']+'\n\n仅使用同签名安装包覆盖更新。','draft':True,'prerelease':False})
    upload=draft['upload_url'].split('{')[0]
    from urllib.parse import quote
    manifest=json.dumps(data,ensure_ascii=False,indent=2).encode('utf-8')
    for name,body,mime in [(apk.name,apk.read_bytes(),'application/vnd.android.package-archive'),(ASSET,manifest,'application/json')]:
        asset=api.call(upload+'?name='+quote(name),method='POST',binary=body,content_type=mime)
        if asset.get('state')!='uploaded' or asset['size']!=len(body):raise RuntimeError('Asset upload verification failed; draft preserved')
    published=api.call('/releases/'+str(draft['id']),'PATCH',{'draft':False,'make_latest':'false'})
    if not owned_release(published):raise RuntimeError('Published release incomplete; no cleanup performed')
    # App-specific markers prevent deletion of other apps, drafts, prereleases or unrelated tags.
    for release in prune_candidates(api.releases()):
        api.call('/releases/'+str(release['id']),'DELETE')
        print('Removed old rhythm release:',release['tag_name'])
    print('Published:',tag,'; retained at most five rhythm releases; Git tags unchanged')
def main():
    if os.environ.get('GITHUB_REPOSITORY')!=REPO:raise RuntimeError('Workflow is scoped to '+REPO)
    folder=Path(__file__).resolve().parent
    data=json.loads((folder/'release.json').read_text(encoding='utf-8'))
    apk=folder/('rhythm_control_'+data['versionName']+'.apk')
    validate(data,apk)
    publish(GitHub(os.environ['GH_TOKEN']),data,apk,os.environ['GITHUB_SHA'])
if __name__=='__main__':main()
