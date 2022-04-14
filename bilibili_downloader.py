import requests
import re
import os
import sys
import time

headers = {
    'referer': 'https://www.bilibili.com',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)\
        Chrome/91.0.4472.114 Safari/537.36'
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
# メイン関数
# --------------------------------------------------
def main():
    print('###############################')
    print('   ビリビリ動画ダウンローダ')
    print('###############################\n')
    print('M: マイリスid(ml[数字])または動画id(BV[文字列])を入力\n >> ', end='')
    ml_title, bvids = get_bvid(input())
    print('M: マイリストのタイトル:', ml_title)
    print('M: ダウンロードする動画数:', len(bvids))
    print('M: ダウンロードする画質:',
          ', '.join(list(quality_dict)[0:8]), '\n >> ',
          end='')
    ql = re.sub(r'[^0-9pK+]', '', input())
    while quality_dict.get(ql) is None:
        print('\nE: 画質の指定に失敗\n >> ', end='')
        ql = input()
    print()
    cookies = get_cookie()
    print('###############################')
    for bvid in bvids:
        print()
        print('###--------------------------------------###')
        video_prop, dl_info = get_durl(bvid, quality_dict[ql], cookies)
        download(ml_title, video_prop, dl_info)
        print(f'M: {TIME}秒待機中...')
        time.sleep(TIME)
        print('###--------------------------------------###')


# --------------------------------------------------
# 絶対パスを相対パスに [入:相対パス, 実行ファイル側or展開フォルダ側 出:絶対パス]
# --------------------------------------------------
def rel2abs_path(filename, attr):
    if attr == 'temp':  # 展開先フォルダと同階層
        datadir = os.path.dirname(__file__)
    elif attr == 'exe':  # exeファイルと同階層の絶対パス
        datadir = os.path.dirname(sys.argv[0])
    else:
        raise print(f'E: 相対パスの引数ミス [{attr}]')
    return os.path.join(datadir, filename).replace(os.path.sep, '/')


# --------------------------------------------------
# API鯖のstatusを確認 [入:マイリスのid 出:マイリス名、ビデオid]
# --------------------------------------------------
def check_stat(response):
    try:
        if response['code'] == 0:
            return
        raise Exception(
            f'W: API server returns | Error: {response["code"]}')
    except Exception as e:
        print(e)


# --------------------------------------------------
# PC上に存在するcookieを探索 [入:None 出:cookieのパス]
# --------------------------------------------------
def find_local_cookie():
    filepath = os.path.join(os.getenv('APPDATA'),
                            'Mozilla', 'Firefox', 'Profiles')
    for cwd, dirs, files in os.walk(filepath):
        for file in files:
            if 'cookies.sqlite' == file:
                filepath = os.path.join(cwd, file)
                break
        else:
            continue
        break
    if 'cookies.sqlite' not in filepath:
        print('W: cookieを取得できませんでした')
        filepath = None
    else:
        print('M: cookieを取得しました')
    return filepath


# --------------------------------------------------
# cookieを取得する [入:None 出:ビリビリ用のcookie]
# --------------------------------------------------
def get_cookie():
    import sqlite3
    import shutil
    import tempfile
    import http.cookiejar

    cookiefile = find_local_cookie()
    if cookiefile is None:
        return ''
    temp_dir = tempfile.gettempdir()
    temp_cookiefile = os.path.join(temp_dir, 'temp_cookiefile.sqlite')
    shutil.copy2(cookiefile, temp_cookiefile)
    cookies = http.cookiejar.MozillaCookieJar()
    con = sqlite3.connect(temp_cookiefile)
    cur = con.cursor()
    cur.execute('''SELECT host, name, value FROM moz_cookies''')
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
# マイリスから動画のリストを取得 [入:マイリスのid 出:マイリス名、ビデオid]
# --------------------------------------------------
def get_bvid(mylist_id):
    mylist_id = re.sub(r'[^0-9a-zA-Z]', '', mylist_id)
    print(mylist_id)
    if 'BV' in mylist_id:  # 動画idの場合は個別ダウンロード
        return 'Individual', [mylist_id]
    elif 'ml' not in mylist_id:  # 例外処理
        print('\nE: リストのidが無効です\n>> ', end='')
        return get_bvid(input())
    url = f'http://api.bilibili.com/x/v3/fav/resource/list?media_id={mylist_id[2:]}&ps=1'
    res = requests.get(url).json()
    check_stat(res)
    ml_title = res['data']['info']['title']  # マイリストの名前
    ml_title = re.sub(r'[\\|/|:|?|.|"|<|>|\|]', ' ', ml_title)
    url = f'http://api.bilibili.com/x/v3/fav/resource/ids?media_id={mylist_id[2:]}'
    res = requests.get(url).json()
    check_stat(res)
    data = res['data']
    bvids = []  # マイリスト内の動画id群
    for row in data:
        bvids.append(row['bv_id'])
    return ml_title, bvids


# --------------------------------------------------
# ダウンロードURLの取得 [入:ビデオid、画質、cookie 出:ビデオのメタデータ、DLするURL]
# --------------------------------------------------
def get_durl(bvid, qn, cookies):
    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
    res = requests.get(url).json()
    check_stat(res)
    video_prop = res['data']
    cid = res['data']['cid']  # ダウンロードするビデオの固有id
    url = f'http://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={qn}'
    res = requests.get(url, cookies=cookies, headers=headers).json()
    check_stat(res)
    data = res.get('data')  # 動画のメタデータ
    if int(data['quality']) < qn:
        print('W: 指定された画質よりも低い画質がDLされます')
    dl_info = data['durl'][0]  # ダウンロードするファイル情報
    print('M: ダウンロード画質:', quality_dict.get(data['quality']))
    return video_prop, dl_info


# --------------------------------------------------
# 動画のダウンロード [入:マイリス名、ビデオのメタデータ、ダウンロード用メタデータ 出:None]
# --------------------------------------------------
def download(ml_title, video_prop, dl_info):
    from tqdm import tqdm
    title = f'{video_prop["owner"]["name"]} - {video_prop["title"]}'
    title = re.sub(r'[\\|/|:|?|"|<|>|\|]', ' ', title)  # ファイル名に使えない文字を削除
    print('M: ダウンロード開始:', title)
    os.makedirs(rel2abs_path(ml_title, 'exe'), exist_ok=True)
    fp = rel2abs_path(os.path.join(ml_title, f'{title}.flv'), 'exe')
    if os.path.isfile(fp):  # ファイルの上書きを阻止
        print('W: すでにファイルが存在しています')
        return
    with open(fp, 'wb') as savefile:
        res = requests.get(dl_info['url'], headers=headers, stream=True)
        pbar = tqdm(total=int(dl_info['size']), unit='B', unit_scale=True)
        for chunk in res.iter_content(chunk_size=1024):
            savefile.write(chunk)
            pbar.update(len(chunk))
        pbar.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print('E: ', e)
    print('M: 終了しました')
    os.system('PAUSE')
