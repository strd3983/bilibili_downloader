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
from colorama import Fore, Style
from tqdm import tqdm as std_tqdm

__version__ = "XXXX.XX.XX"
tqdm = partial(std_tqdm, dynamic_ncols=True)

TIME: int = 5
UNUSE_STR: str = r'[\\/:*?."<>|]+'
HEADERS: dict = {
    "referer": "https://www.bilibili.com",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)\
                   Chrome/94.0.4606.61 Safari/537.36",
}
DEFAULT_CONF: dict = {"exist_ok": False, "codec": "AV1", "ffmpeg_path": ""}
QUALITY_DICT: dict = {
    116: "1080p60",
    74: "720p60",
    112: "1080p+",
    80: "1080p",
    64: "720p",
    32: "480p",
    16: "360p",
    13: "AV1",
    12: "HEVC",
    7: "AVC",
}
QUALITY_DICT = {**QUALITY_DICT, **{v: k for k, v in QUALITY_DICT.items()}}


def main() -> None:
    """
    メイン関数
    """

    print("\n###############################")
    print("   ビリビリ動画ダウンローダ")
    print(f"    version: {__version__}")
    print("###############################\n")
    check_version()
    configs = check_config()
    check_ffmpeg()
    cookies = get_cookie()
    error_bvid: list[str] = ["前回失敗した動画id (コピペで一括再DL)->"]
    while True:
        print("[M] マイリスid: ml[数字] または動画id: BV[文字列] を入力")
        print("[M] 終了する場合はexitを入力")
        ml_title, bvids = get_bvids(input(" >> "))
        if ml_title == "" and bvids == []:
            break
        print("[M] マイリストのタイトル:", ml_title)
        print("[M] ダウンロードする動画数:", len(bvids))
        print("[M] ダウンロードする画質:", *list(QUALITY_DICT.keys())[10:17])
        ql = re.sub(r"[^0-9ampK+]", "", input(">> "))
        while QUALITY_DICT.get(ql) is None:
            call_backtrace("[E] 画質の指定に失敗. 再度入力")
            ql = input(">> ")
        for i, bvid in enumerate(bvids):
            print(f"### ----------------| {i+1}/{len(bvids)} |---------------- ###")
            try:
                video_props = get_cids(bvid)
                for video_prop in video_props:
                    tic = time.time()  # 開始時刻
                    download(
                        configs,
                        ml_title,
                        video_prop,
                        get_durl(configs, bvid, video_prop["cid"], QUALITY_DICT[ql], cookies),
                    )
                    toc = time.time()  # 開始時刻
                    if toc - tic < TIME:
                        print(f"[M] {TIME}秒待機中...")
                        time.sleep(TIME)
            except Exception:
                call_backtrace()
                error_bvid.append(bvid)
        print("### -------------------------------------- ###")
    # write error bvid to txt log
    if len(error_bvid) != 1:
        with open(rel2abs_path("error_log.txt", "exe"), "w", encoding="UTF-8") as f:
            print(*error_bvid, file=f)


def call_backtrace(msg: str = "", end: str = "\n") -> None:
    """
    例外エラー発生時に表示やトレースバックを行う [入: エラーメッセージ 出: None]
    """
    import backtrace

    STYLES = {
        "backtrace": " | " + Fore.YELLOW + "{0}",
        "line": " | " + Fore.RED + Style.BRIGHT + "{0}",
        "context": Fore.GREEN + Style.BRIGHT + "{0}",
        "error": " | " + Fore.RED + Style.BRIGHT + "{0}",
    }

    if msg[:3] == "[E]":
        print(Fore.RED + Style.BRIGHT + msg, end=end)
    elif msg[:3] == "[W]":
        print(Fore.YELLOW + Style.BRIGHT + msg, end=end)
    else:
        tpe, v, tb = sys.exc_info()
        print(Fore.RED + Style.BRIGHT + "[E]" + Style.RESET_ALL)
        backtrace.hook(strip_path=True, align=True, styles=STYLES, tb=tb, tpe=tpe, value=v)
    print(Style.RESET_ALL, end="")


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
    API鯖のstatusを確認 [入:jsonレスポンス 出:None]
    """

    if response["code"] == 0:
        return
    elif response["code"] == -101:
        call_backtrace("[W] ログインできませんでした. FireFoxにてログインしているか確認してください")
        return
    call_backtrace(f"[E] API server returns | Error: {response['code']}")
    raise Exception(f"Message: {response['message']}")


def check_version() -> None:
    """
    プログラムのバージョンチェックを行う [入:None 出:None]
    """
    from datetime import date

    try:
        repo = "https://api.github.com/repos/strd3983/bilibili_downloader"
        res = requests.get(f"{repo}/releases/latest").json()
        tag = res["name"]
        basehead = f"v{__version__}...{tag}"
        latest = date(*[int(x) for x in tag[1:].split(".")])
        now = date(*[int(x) for x in __version__.split(".")])

        if now < latest:
            durl = res["assets"][1] if os.name == "nt" else res["assets"][0]
            call_backtrace(f"[W] ソフトウェアのアップデートが可能です: v{__version__} -> {tag}")
            call_backtrace(f"[W] ダウンロード: {durl['browser_download_url']}")
            res = requests.get(f"{repo}/compare/{basehead}").json()
            print("[M] 変更履歴 (#番号はissue番号を参照: https://bit.ly/3IKYi1j)")
            print("\n".join(["    " + commit["commit"]["message"] for commit in res["commits"]]))
    except ValueError:
        pass
    except Exception:
        call_backtrace()


def check_config() -> dict:
    """
    yamlファイルから設定を読み込む [入:None 出: 設定]
    """
    import toml

    conf: dict = DEFAULT_CONF

    p = rel2abs_path("config.toml", "exe")
    if os.path.exists(p):
        # Open the toml file and load it into the CONFIG dictionary
        with open("config.toml", "r", encoding="utf-8") as f:
            conf = toml.load(f)

        # Print the CONFIG dictionary to verify the content
        print("[M] 設定ファイルを読み込みました")
    else:
        print("[M] 設定ファイル (config.toml) がありません. デフォルとの値を使用します.")
    print(f"[M] {str(conf)[1:-1]}")

    return conf


def check_ffmpeg() -> None:
    """
    ffmpegの確認 [入:None 出:None]
    """

    if "ffmpeg" in os.environ.get("PATH", ""):
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
        res = requests.get(url, headers=HEADERS, stream=True)
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
        assert ffmpeg, "自動ダウンロード失敗. ffmpegをダウンロードしてffmpegフォルダ内に配置してください."

    os.environ["PATH"] = f"{os.path.dirname(ffmpeg[0])};{os.environ['PATH']}"


def get_cookie() -> dict:
    """
    cookieを取得する [入:None 出:ビリビリ用のcookie]
    """

    def _find_local_cookie() -> str:
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
            call_backtrace("[W] cookieを取得できませんでした")
            return ""
        else:
            print("[M] cookieを取得しました")
        return filepath

    import http.cookiejar
    import shutil
    import sqlite3
    import tempfile
    from json import JSONDecodeError

    cookiefile = _find_local_cookie()
    if cookiefile == "":
        return {}
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
        res = requests.get(url, cookies=bilibili_cookies, headers=HEADERS).json()
        check_stat(res)
        print("[M]", Fore.GREEN + Style.BRIGHT + res["data"]["uname"] + Style.RESET_ALL, "としてログイン")
    except JSONDecodeError:
        call_backtrace("[W] サブのurlが使用されます")
        url = "https://api.bilibili.com/nav"
        res = requests.get(url, cookies=bilibili_cookies, headers=HEADERS).json()
        check_stat(res)
        print("[M]", Fore.GREEN + Style.BRIGHT + res["data"]["uname"] + Style.RESET_ALL, "としてログイン")
    finally:
        return bilibili_cookies


def get_bvids(mylist_id: str) -> tuple[str, list]:
    """
    マイリスから動画のリストを取得 [入:マイリスのid 出:マイリス名, ビデオid]
    """

    if "exit" == mylist_id:
        return "", []
    if "BV" in mylist_id:  # 動画idの場合は個別ダウンロード
        return "Individual", re.findall(r"BV[A-Za-z0-9]+", mylist_id)
    elif "ml" not in mylist_id:  # 例外処理
        call_backtrace("[E] リストのidが無効です. 再度入力してください.")
        return get_bvids(input(" >> "))
    mylist_ids = re.findall(r"ml[A-Za-z0-9]+", mylist_id)
    bvids = []  # マイリスト内の動画id群
    ml_title = ""
    for mylist_id in mylist_ids:
        url = f"http://api.bilibili.com/x/v3/fav/resource/list?media_id={mylist_id[2:]}&ps=1"
        res = requests.get(url, headers=HEADERS).json()
        check_stat(res)
        ml_title += res["data"]["info"]["title"]  # マイリストの名前
        ml_title = re.sub(UNUSE_STR, " ", ml_title)
        url = f"http://api.bilibili.com/x/v3/fav/resource/ids?media_id={mylist_id[2:]}"
        res = requests.get(url, headers=HEADERS).json()
        check_stat(res)
        data = res["data"]
        for row in data:
            bvids.append(row["bv_id"])
    return ml_title, bvids


def get_cids(bvid: str) -> list:
    """
    動画プロパティ (cidなど) の取得 [入:ビデオid, 画質, cookie 出:ビデオのメタデータ]
    """

    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    res = requests.get(url, headers=HEADERS).json()
    if res["code"] == -404:  # 日本からアクセスを拒否されているものを回避
        # TODO: 代替串を探す (https://www.bilibili.com/video/BV1tU4y1376A/)
        print("[M] プロキシ鯖を経由")
        url = f"http://www.ekamali.com/index.php?q={url}&hl=3c0"
        res = requests.get(url, headers=HEADERS).json()
    check_stat(res)
    video_props = []
    for page in res["data"]["pages"]:
        video_prop = res["data"].copy()
        video_prop["cid"] = page["cid"]
        if len(res["data"]["pages"]) == 1:  # 一つの場合は動画タイトル
            title = f'{video_prop["owner"]["name"]} - {video_prop["title"]}'
            title = re.sub(UNUSE_STR, " ", title)  # ファイル名に使えない文字を削除
        else:  # 複数ページがある場合はページタイトル
            video_prop["title"] = page["part"]
            title = f'{video_prop["owner"]["name"]} - {video_prop["title"]}'
            title = re.sub(UNUSE_STR, " ", title)  # ファイル名に使えない文字を削除
        video_prop["fname"] = title  # filename を辞書に追加
        video_props.append(video_prop)
    return video_props


def get_durl(CONFIG: dict, bvid: str, cid: str, qn: int, cookies: dict) -> list:
    """
    ダウンロードURLの取得 [入:設定, ビデオid, 画質, cookie 出:DLする情報]
    """

    def _check_quality(data: dict, qn: int, codec: str) -> tuple:
        """
        画質とコーデックを指定する [入: jsonデータ, 画質 出: 動画と音声データ情報]
        """

        video = data["dash"]["video"][0] if data["dash"]["video"] is not None else None
        audio = data["dash"]["audio"][0] if data["dash"]["audio"] is not None else None
        if qn == 0 or video is None:
            return None, audio
        for v in data["dash"]["video"]:
            if v["id"] != qn:  # 指定した画質以外は無視
                continue
            if v["codecid"] == QUALITY_DICT[codec]:  # コーデックの指定がある場合は優先
                video = v
                break
            if video["codecid"] <= v["codecid"]:  # AV1, HEVC, AVCの順に優先度
                video = v
        # 画質チェック
        if video["id"] != qn:
            if qn not in data["accept_quality"]:
                call_backtrace(
                    "[W] 指定された画質 ("
                    + QUALITY_DICT[qn]
                    + ") は動画 ("
                    + " ".join([QUALITY_DICT[v] for v in data["accept_quality"]])
                    + ") に存在しません"
                )
            else:
                call_backtrace("[W] 720p60や1080pは一般会員, 1080p60以上は有料会員のログインが必要です")
        # コーデックチェック
        if video["codecid"] != QUALITY_DICT[codec]:
            call_backtrace(f"[W] 指定のコーデック ({codec}) は動画に存在しません")
        # ダウンロードするファイル情報
        print(f"[M] ダウンロード画質: {QUALITY_DICT[video['id']]} ({QUALITY_DICT[video['codecid']]})")

        return video, audio

    options = f"bvid={bvid}&cid={cid}&qn={qn}&fnval={16|2048}&fnver=0&fourk=1&voice_balance=1"
    url = "http://api.bilibili.com/x/player/wbi/playurl?" + options
    res = requests.get(url, cookies=cookies, headers=HEADERS).json()
    check_stat(res)
    data = res["data"]  # 動画のメタデータ
    data = _check_quality(data, qn, CONFIG["codec"])
    return data


def download(CONFIG: dict, ml_title: str, video_prop: dict, dl_info: list) -> None:
    """
    動画のダウンロード [入:設定, マイリス名, ビデオのメタデータ, ダウンロード用メタデータ 出:None]
    """

    def _tag2mp3(fp: str, prop: dict) -> None:
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
        response = requests.get(prop["pic"], headers=HEADERS)
        audio.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=response.content))
        audio.save()

    video, audio = dl_info
    print("[M]", video_prop["fname"])
    # setup directory
    os.makedirs(rel2abs_path(ml_title, "exe"), exist_ok=True)
    # temp files
    fp_video = rel2abs_path(os.path.join("video.m4s"), "temp")
    fp_audio = rel2abs_path(os.path.join("audio.m4s"), "temp")
    if audio is None and video is None:  # 情報がない場合
        return
    elif video is None:  # 音声のみの場合
        suffix = "mp3"
        fps = [fp_audio]
        dl_info = [dl_info[1]]
        fp_merge = rel2abs_path(os.path.join(f"merge.{suffix}"), "temp")
        cmd = f"ffmpeg -i {fp_audio} -ab {dl_info[0]['bandwidth']} -f {suffix} {fp_merge}"
    elif audio is None:  # 動画のみの場合
        suffix = "mp4"
        fps = [fp_video, fp_audio]
        fp_merge = rel2abs_path(os.path.join("merge.mp4"), "temp")
        cmd = f"ffmpeg -i {fp_video} -c:v copy -f mp4 {fp_merge}"
    else:  # 動画, 音声両方ある場合
        suffix = "mp4"
        fps = [fp_video, fp_audio]
        fp_merge = rel2abs_path(os.path.join(f"merge.{suffix}"), "temp")
        cmd = f"ffmpeg -i {fp_video} -i {fp_audio} -c:v copy -c:a copy -f {suffix} {fp_merge}"
    # output path
    fp = rel2abs_path(os.path.join(ml_title, f"{video_prop['fname']}.{suffix}"), "exe")

    # ファイルの上書きを阻止
    if os.path.isfile(fp) and not CONFIG["exist_ok"]:
        call_backtrace("[W] すでにファイルが存在しています")
        return

    # download
    for data, f in zip(dl_info, fps):
        if data is None:
            continue
        res = requests.get(data["baseUrl"], headers=HEADERS, stream=True)
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
    shutil.move(fp_merge, fp)

    if audio is None:
        os.remove(fp_video)
    elif video is None:
        # tagging audio
        _tag2mp3(fp, video_prop)
        os.remove(fp_audio)
    else:
        os.remove(fp_video)
        os.remove(fp_audio)


if __name__ == "__main__":
    # 文字コード化けを起こすのを回避
    if os.name == "nt":
        os.system("chcp 65001")
        os.system("cls")
    try:
        main()
    except Exception:
        call_backtrace()
    print("[M] 終了しました")
    if os.name == "nt":
        os.system("PAUSE")
