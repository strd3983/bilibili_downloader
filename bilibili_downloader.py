import glob
import os
import re
import shutil
import subprocess as sb
import sys
import time
from functools import partial
from typing import Tuple, cast

import requests
from tqdm import tqdm as std_tqdm

__version__ = "XXXX.XX.XX"

tqdm = partial(std_tqdm, dynamic_ncols=True)
headers: dict = {
    "referer": "https://www.bilibili.com",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)\
                   Chrome/94.0.4606.61 Safari/537.36",
}

quality_dict: dict = {
    "1080p60": 116,
    "720p60": 74,
    "1080p+": 112,
    "1080p": 80,
    "720p": 64,
    "480p": 32,
    "360p": 16,
    "mp3": 0,
    116: "1080p60",
    74: "720p60",
    112: "1080p+",
    80: "1080p",
    64: "720p",
    32: "480p",
    16: "360p",
}
TIME: int = 5
unuse_str: str = r'[\\/:*?."<>|]+'


def main() -> None:
    """
    メイン関数
    """

    print("\n###############################")
    print("   ビリビリ動画ダウンローダ")
    print(f"    version: {__version__}")
    print("###############################\n")
    check_version()
    check_ffmpeg()
    cookies = get_cookie()
    error_bvid: list[str] = ["前回失敗した動画id"]
    while True:
        print("[M] マイリスid: ml[数字] または動画id: BV[文字列] を入力. 終了する場合はexitを入力.")
        ml_title, bvids = get_bvid(input(" >> "))
        if ml_title is None and bvids is None:
            break
        print("[M] マイリストのタイトル:", ml_title)
        print("[M] ダウンロードする動画数:", len(bvids))
        print("[M] ダウンロードする画質:", *list(quality_dict.keys())[:8])
        print("[M] mp3を指定すると音声ファイルのみがダウンロード")
        print(" >> ", end="")
        ql = re.sub(r"[^0-9ampK+]", "", input())
        while quality_dict.get(ql) is None:
            print("[E] 画質の指定に失敗. 再度入力\n >> ", end="")
            ql = input()
        for i, bvid in enumerate(bvids):
            print(f"###----------------{i+1}/{len(bvids)}----------------###")
            try:
                video_prop, dl_info = get_content(bvid, quality_dict[ql], cookies)
                download(ml_title, video_prop, dl_info, ql)
            except Exception as e:
                print(f"[E] {e}")
                error_bvid.append(bvid)
            print(f"[M] {TIME}秒待機中...")
            time.sleep(TIME)
        print("###--------------------------------------###")
    # write error bvid to txt log
    if len(error_bvid) != 1:
        with open(rel2abs_path("error_log.txt", "exe"), "w", encoding="UTF-8") as f:
            print(*error_bvid, file=f)


def rel2abs_path(filename: str, attr: str) -> str:
    """
    絶対パスを相対パスに [入:相対パス, exe側 or temp側 出:絶対パス]
    """

    if attr == "temp":  # 展開先フォルダと同階層
        datadir = os.path.dirname(__file__)
    elif attr == "exe":  # exeファイルと同階層の絶対パス
        datadir = os.path.dirname(sys.argv[0])
    else:
        raise Exception(f"[E] 相対パスの引数ミス [{attr}]")
    return os.path.join(datadir, filename).replace(os.path.sep, "/")


def check_stat(response: dict) -> None:
    """
    API鯖のstatusを確認 [入:マイリスのid 出:マイリス名、ビデオid]
    """

    try:
        if response["code"] == 0:
            return
        elif response["code"] == -101:
            print("[W] ログインできませんでした. FireFoxにてログインしているか確認してください")
            return
        raise Exception(f'[W] API server returns | Error: {response["code"]}')
    except Exception as e:
        print(e)


def check_ffmpeg() -> None:
    """
    ffmpegの確認 []
    """

    if "ffmpeg" in os.environ.get("PATH"):
        return

    ffmpeg = glob.glob(rel2abs_path("ffmpeg/bin/ffmpeg*", "exe"), recursive=True)

    if not ffmpeg:
        print("[M] ffmpegが見つからないため自動ダウンロードします")

        # set path
        if os.name == "nt":
            file = "ffmpeg-master-latest-win64-lgpl-shared.zip"
        else:
            file = "ffmpeg-master-latest-linux64-lgpl-shared.tar.xz"
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/" + file
        dir = file.split(".")[0]
        file = rel2abs_path(file, "exe")
        dir = rel2abs_path(dir, "exe")

        # ffmpeg download
        res = requests.get(url, headers=headers, stream=True)
        pbar = tqdm(
            total=int(res.headers.get("content-length", 0)),
            unit="B",
            unit_scale=True,
            bar_format="{l_bar}{bar:10}{r_bar}{bar:-10b}",
            desc="[M] " + "ffmpeg.zip",
        )
        with open(file, "wb") as savefile:
            for chunk in res.iter_content(chunk_size=32 * 1024):
                savefile.write(chunk)
                pbar.update(len(chunk))
            pbar.close()

        # unarchive
        if os.name == "nt":
            from zipfile import ZipFile

            with ZipFile(file) as zf:
                zf.extractall()
        else:
            import tarfile

            with tarfile.open(file) as tf:
                tf.extractall()

        os.remove(file)
        os.rename(dir, rel2abs_path("ffmpeg", "exe"))
        # check again
        ffmpeg = glob.glob(rel2abs_path("ffmpeg/bin/ffmpeg*", "exe"), recursive=True)
        assert ffmpeg, "[E] 自動ダウンロード失敗. ffmpegをダウンロードしてffmpegフォルダ内に配置してください."

    os.environ["PATH"] = f"{os.path.dirname(ffmpeg[0])};{os.environ['PATH']}"


def check_version() -> None:
    from datetime import date

    try:
        response = requests.get("https://api.github.com/repos/strd3983/bilibili_downloader/releases/latest")
        tag = response.json()["name"]
        latest = date(*[int(x) for x in tag[1:].split(".")])
        now = date(*[int(x) for x in __version__.split(".")])

        if now < latest:
            print(f"[W] ソフトウェアのアップデートが可能です: v{__version__} -> {tag}")
            print("[W] https://github.com/strd3983/bilibili_downloader/releases/latest")
    except Exception as e:
        print(f"[E] {e}")


def find_local_cookie() -> str:
    """
    PC上に存在するcookieを探索 [入:None 出:cookieのパス]
    """

    filepath = os.path.join(cast(str, os.getenv("APPDATA")), "Mozilla", "Firefox", "Profiles")
    for cwd, dirs, files in os.walk(filepath):
        for file in files:
            if "cookies.sqlite" == file:
                filepath = os.path.join(cwd, file)
                break
        else:
            continue
        break
    if "cookies.sqlite" not in filepath:
        print("[W] cookieを取得できませんでした")
        return None
    else:
        print("[M] cookieを取得しました")
    return filepath


def get_cookie() -> dict:
    """
    cookieを取得する [入:None 出:ビリビリ用のcookie]
    """

    import http.cookiejar
    import shutil
    import sqlite3
    import tempfile
    from json import JSONDecodeError

    cookiefile = find_local_cookie()
    if cookiefile is None:
        return ""
    temp_dir = tempfile.gettempdir()
    temp_cookiefile = os.path.join(temp_dir, "temp_cookiefile.sqlite")
    shutil.copy2(cookiefile, temp_cookiefile)
    cookies = http.cookiejar.MozillaCookieJar()
    con = sqlite3.connect(temp_cookiefile)
    cur = con.cursor()
    cur.execute("SELECT host, name, value FROM moz_cookies")
    cookies = cur.fetchall()  # type: ignore
    cur.close
    con.close

    names = []
    values = []
    for cookie in cookies:
        # cookie:('host', 'name', 'value')
        c = cast(Tuple[str, str, str], cookie)
        if c[0] == ".bilibili.com":
            names.append(c[1])
            values.append(c[2])

    bilibili_cookies = dict(zip(names, values))

    # display username who logged in
    url = "https://api.bilibili.com/x/web-interface/nav"
    try:
        res = requests.get(url, cookies=bilibili_cookies, headers=headers).json()
        check_stat(res)
        print("[M]", res["data"]["uname"], "としてログイン")
    except JSONDecodeError:
        print("[W] サブのurlが使用されます")
        url = "https://api.bilibili.com/nav"
        res = requests.get(url, cookies=bilibili_cookies, headers=headers).json()
        check_stat(res)
        print("[M]", res["data"]["uname"], "としてログイン")
    finally:
        return bilibili_cookies


def get_bvid(mylist_id: str) -> tuple[str, list]:
    """
    マイリスから動画のリストを取得 [入:マイリスのid 出:マイリス名、ビデオid]
    """

    if "exit" == mylist_id:
        return None, None
    if "BV" in mylist_id:  # 動画idの場合は個別ダウンロード
        return "Individual", re.findall(r"BV[A-Za-z0-9]+", mylist_id)
    elif "ml" not in mylist_id:  # 例外処理
        print("[E] リストのidが無効です. 再度入力してください.")
        return get_bvid(input(" >> "))
    mylist_id = re.findall(r"ml[A-Za-z0-9]+", mylist_id)[0]
    url = f"http://api.bilibili.com/x/v3/fav/resource/list?media_id={mylist_id[2:]}&ps=1"
    res = requests.get(url).json()
    check_stat(res)
    ml_title = res["data"]["info"]["title"]  # マイリストの名前
    ml_title = re.sub(unuse_str, " ", ml_title)
    url = f"http://api.bilibili.com/x/v3/fav/resource/ids?media_id={mylist_id[2:]}"
    res = requests.get(url).json()
    check_stat(res)
    data = res["data"]
    bvids = []  # マイリスト内の動画id群
    for row in data:
        bvids.append(row["bv_id"])
    return ml_title, bvids


def get_content(bvid: str, qn: int, cookies: dict) -> tuple[dict, list]:
    """
    ダウンロードURLの取得 [入:ビデオid、画質、cookie 出:ビデオのメタデータ、DLするURL]
    """

    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    res = requests.get(url).json()
    if res["code"] == -404:  # 日本からアクセスを拒否されているものを回避
        print("[M] プロキシ鯖を経由")
        url = f"http://www.ekamali.com/index.php?q={url}&hl=3c0"
        res = requests.get(url).json()
    check_stat(res)
    video_prop = res["data"]
    title = f'{video_prop["owner"]["name"]} - {video_prop["title"]}'
    title = re.sub(unuse_str, " ", title)  # ファイル名に使えない文字を削除
    print("[M]", title)

    cid = res["data"]["cid"]  # ダウンロードするビデオの固有id
    options = f"bvid={bvid}&cid={cid}&qn={qn}&fnval={16|2048}&fnver=0&fourk=1&voice_balance=1"
    url = "http://api.bilibili.com/x/player/playurl?" + options
    res = requests.get(url, cookies=cookies, headers=headers).json()
    check_stat(res)
    data = res["data"]  # 動画のメタデータ
    data = check_quality(data, qn)
    return video_prop, data


def check_quality(data: dict, qn: int) -> tuple:
    # video
    video = data["dash"]["video"][0]
    audio = data["dash"]["audio"][0]
    if qn == 0:
        return video, audio
    for v in data["dash"]["video"]:
        # 指定した画質以外は無視
        if v["id"] != qn:
            continue
        # AV1, HEVC, AVCの順に優先度
        if video["codecid"] < v["codecid"]:
            video = v

    # 画質チェック
    if video["id"] != qn:
        if qn not in data["accept_quality"]:
            print("[W] 指定された画質が当動画に存在しません")
        else:
            print("[W] 720p60や1080pは一般会員, 1080p60以上は有料会員のログインが必要です")
    # ダウンロードするファイル情報 (HEVC優先)
    print("[M] ダウンロード画質:", quality_dict.get(video["id"]))

    return video, audio


def download(ml_title: str, video_prop: dict, dl_info: dict, ql: str) -> None:
    """
    動画のダウンロード [入:マイリス名、ビデオのメタデータ、ダウンロード用メタデータ 出:None]
    """

    # setup directory
    os.makedirs(rel2abs_path(ml_title, "exe"), exist_ok=True)
    # temp files
    fp_video = rel2abs_path(os.path.join("video.m4s"), "temp")
    fp_audio = rel2abs_path(os.path.join("audio.m4s"), "temp")
    if ql in ["mp3", "m4a"]:
        suffix = ql
        fps = [fp_audio]
        dl_info = [dl_info[1]]
        fp_merge = rel2abs_path(os.path.join(f"merge.{suffix}"), "temp")
        cmd = f"ffmpeg -i {fp_audio} -ab {dl_info[0]['bandwidth']} -f {suffix} {fp_merge}"
    else:
        suffix = "mp4"
        fps = [fp_video, fp_audio]
        fp_merge = rel2abs_path(os.path.join(f"merge.{suffix}"), "temp")
        cmd = f"ffmpeg -i {fp_video} -i {fp_audio} -c:v copy -c:a copy -f {suffix} {fp_merge}"
    # output path
    fname = f"{video_prop['owner']['name']} - {video_prop['title']}"
    fname = re.sub(unuse_str, " ", fname)  # ファイル名に使えない文字を削除
    fp = rel2abs_path(os.path.join(ml_title, f"{fname}.{suffix}"), "exe")

    # ファイルの上書きを阻止
    if os.path.isfile(fp):
        print("[W] すでにファイルが存在しています")
        return

    # download
    for data, f in zip(dl_info, fps):
        res = requests.get(data["baseUrl"], headers=headers, stream=True)
        pbar = tqdm(
            total=int(res.headers.get("content-length", 0)),
            unit="B",
            unit_scale=True,
            bar_format="{l_bar}{bar:10}{r_bar}{bar:-10b}",
            desc="[M] " + data["codecs"].split(".")[0],
        )
        with open(f, "wb") as savefile:
            for chunk in res.iter_content(chunk_size=32 * 1024):
                savefile.write(chunk)
                pbar.update(len(chunk))
            pbar.close()

    # merge and convert web files into mp4 or mp3 file
    print("[M] ファイルを変換中...")
    sb.run(cmd + " -loglevel quiet")

    # tagging audio
    if ql == "mp3":
        tag2mp3(fp_merge, video_prop)

    try:
        shutil.move(fp_merge, fp)
        os.remove(fp_audio)
        os.remove(fp_video)
    except Exception:
        pass


def tag2mp3(fp: str, prop: dict) -> None:
    from mutagen.id3 import APIC, ID3, TIT2, TPE1, error
    from mutagen.mp3 import MP3

    audio = MP3(fp, ID3=ID3)

    try:
        audio.add_tags()
    except error:
        pass

    # title
    audio.tags.add(TIT2(encoding=3, text=prop["title"]))
    # artist
    audio.tags.add(TPE1(encoding=3, text=prop["owner"]["name"]))
    # cover art
    print("[M] サムネイルをダウンロード中...")
    response = requests.get(prop["pic"])
    audio.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=response.content))
    audio.save()


if __name__ == "__main__":
    # 文字コード化けを起こすのを回避
    if os.name == "nt":
        os.system("chcp 65001")
        os.system("cls")
    try:
        main()
    except Exception as e:
        print("[E] ", e)
    print("[M] 終了しました")
    if os.name == "nt":
        os.system("PAUSE")
