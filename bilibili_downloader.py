import requests
import os
import sys
import time
# ml1532880516

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
headers = {
    'user-Agent': user_agent
}

quality_dict = {
    '4K': 120,
    '1080p60': 116,
    '720p60': 74,
    '1080p+': 112,
    '1080p': 80,
    '720p': 64,
    '480p': 32,
    '360p': 16,
    120: '4K',
    116: '1080p60',
    74: '720p60',
    112: '1080p+',
    80: '1080p',
    64: '"720p"',
    32: '480p',
    16: '360p'
}
TIME = 5


# --------------------------------------------------
# 絶対パスを相対パスに (pyinstallerとjupyter notebook対応)
# --------------------------------------------------
def main():
    print('###### マイリストのidを入力 ######')
    ml_title, bvids = get_bvid()
    print('マイリストのタイトル:', ml_title)
    print('ダウンロードする動画数:', len(bvids))
    cookies = get_cookie()
    print('###############################')
    for bvid in bvids:
        print('待機中...')
        time.sleep(TIME)
        print('###--------------------------------------###')
        video_prop, dl_info = get_durl(bvid, cookies)
        download(ml_title, video_prop, dl_info)
        print('###--------------------------------------###')


# --------------------------------------------------
# 絶対パスを相対パスに (pyinstallerとjupyter notebook対応)
# --------------------------------------------------
def rel2abs_path(filename):
    if getattr(sys, 'frozen', False):
        # The application is frozen
        datadir = os.path.dirname(sys.executable)
    else:
        # The application is not frozen
        datadir = os.path.dirname(__file__)
    return os.path.join(datadir, filename)


# --------------------------------------------------
# PC上に存在するcookieを探索
# --------------------------------------------------
def find_local_cookie():
    fp = os.path.join(os.getenv('APPDATA'), 'Mozilla', 'Firefox', 'Profiles')
    for cwd, dirs, files in os.walk(fp):
        for file in files:
            if 'cookies.sqlite' == file:
                fp = os.path.join(cwd, file)
                break
        else:
            continue
        break
    print('用いたcookieデータの場所:', fp)
    return fp


# --------------------------------------------------
# cookieを取得する
# --------------------------------------------------
def get_cookie():
    import sqlite3
    import shutil
    import tempfile
    import http.cookiejar

    cookiefile = find_local_cookie()
    temp_dir = tempfile.gettempdir()
    temp_cookiefile = os.path.join(temp_dir, 'temp_cookiefile.sqlite')
    shutil.copy2(cookiefile, temp_cookiefile)
    cookies = http.cookiejar.MozillaCookieJar()
    con = sqlite3.connect(temp_cookiefile)
    cur = con.cursor()
    cur.execute("""SELECT host, name, value FROM moz_cookies""")
    cookies = cur.fetchall()
    cur.close
    con.close

    names = []
    values = []
    for cookie in cookies:
        # cookie:('host', 'name', 'value')
        if cookie[0] == '.bilibili.com':
            names.append(cookie[1])
            values.append(cookie[2])

    bilibili_cookies = dict(zip(names, values))
    return bilibili_cookies


# --------------------------------------------------
# マイリストからダウンロードする動画のリストを取得
# --------------------------------------------------
def get_bvid():
    mylist_id = input()  # ダウンロードするビデオのid
    url = f'http://api.bilibili.com/x/v3/fav/resource/list?media_id={mylist_id[2:]}&ps=1'
    res = requests.get(url).json()
    ml_title = res['data']['info']['title']  # マイリストの名前
    url = f'http://api.bilibili.com/x/v3/fav/resource/ids?media_id={mylist_id[2:]}'
    res = requests.get(url).json()
    data = res['data']
    bvids = []  # マイリスト内の動画id群
    for row in data:
        bvids.append(row['bv_id'])
    return ml_title, bvids


# --------------------------------------------------
# ダウンロードURLの取得 [入:ビデオid 出:ビデオのメタデータ、DLするURL]
# --------------------------------------------------
def get_durl(bvid, cookies):
    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
    res = requests.get(url).json()
    video_prop = res['data']
    cid = res['data']['cid']  # ダウンロードするビデオの固有id
    qn = quality_dict.get('360p')
    url = f'http://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={qn}'
    res = requests.get(url, cookies=cookies, headers=headers).json()
    data = res.get('data')  # 動画のメタデータ
    if int(data['quality']) < qn:
        print('注意:指定された画質よりも低い画質がDLされます')
    dl_info = data['durl'][0]  # ダウンロードするファイル情報

    print('利用可能:', data['accept_description'])
    print('ダウンロード:', quality_dict.get(data['quality']))
    print('利用可能:', dl_info['url'])
    return video_prop, dl_info


# --------------------------------------------------
# 動画のダウンロード
# --------------------------------------------------
def download(ml_title, video_prop, dl_info):
    from tqdm import tqdm
    title = f'{video_prop["owner"]["name"]} - {video_prop["title"]}'
    print('ダウンロード開始:', title)
    type = 'flv'
    os.makedirs(rel2abs_path(ml_title), exist_ok=True)
    fp = rel2abs_path(os.path.join(ml_title, f'{title}.{type}'))
    with open(fp, 'wb+') as file:
        pbar = tqdm(total=int(dl_info['size']), unit='B', unit_scale=True)
        for chunk in requests.get(
                dl_info['url'],
                stream=True).iter_content(
                chunk_size=1024):
            ff = file.write(chunk)
            pbar.update(len(chunk))
        pbar.close()


if __name__ == "__main__":
    main()
