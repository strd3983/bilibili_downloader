# Bilibili Video and Mylist Downloader

## Features

ビリビリ動画に投稿された動画をダウンロードする.  
動画id (BVやAVから始まる)やマイリストid (mlから始まる)に対応. アカウントがある場合はその会員レベルに応じて高画質DLも可能.  
初回は [導入](#installation) を参照してセットアップをし, 以降は[使い方](#usage)を参考に.

## Todo List

- [x] 個別ダウンロード
- [x] マイリストの一括ダウンロード
- [x] 複数ページのダウンロード
- [x] 上書き保存するかどうか選択
- [x] コーデックの指定 (AV1, HEVC, AVC)
- [ ] ダウンロード履歴管理
- [ ] FireFoxを必要としないログイン情報の取得

## Installation

1. [こちら](https://github.com/strd3983/bilibili_downloader/releases/latest)からzipファイルをダウンロードし解凍
2. 必要に応じて[`config.toml`](config.toml)ファイルを作成し, カスタマイズする (以下の表を参照).
3. bilibiliアカウントがある方は以下の手法で1080p以上の動画やプライベートマイリスをダウンロードできる.
   1. [FireFox](https://www.mozilla.org/firefox/new/)をインストール
   2. FireFoxにて [bilibili.com](https://www.bilibili.com) にログインする (数か月に一度ログインする必要がある)

| 変数名   | 値               | 概要                                                   |
| -------- | ---------------- | ------------------------------------------------------ |
| exist_ok | [true, false]    | 上書き保存を許可するかどうか.                          |
| codec    | [AV1, HEVC, AVC] | ダウンロードするコーデック. H.265(AV1, HEVC)かH.264か. |

## Usage

1. ダウンロードしたexeをダブルクリックすると動画idまたはマイリスidを求められるので入力.  
`https://www.bilibili.com/festival/VRSummerSuper?bvid=BV1wt4y1P78e` のようなURLのコピペからも自動的にidを抜粋してくれる.  
2. 画質値の入力が求められるので入力する.  
なお表示されているものでも元動画が対応していなかったりアカウントに権限がない場合は自動的に可能な画質でダウンロードされる.
3. 単体の動画であれば「Individual」, マイリスであればマイリス名のフォルダに動画保存される.

## Build

### 1. Python環境を構築

仮想環境にてインストール.  Pythonのバージョンは3.7推奨. Pyenv+PipenvまたはPyenv+Poetry推奨.

```bash
pipenv install --dev
```

### 2. Pythonをgccでビルドする

nuitkaを用いてPythonを必要としないバイナリファイルをビルドすることができる.

```ps
nuitka --onefile .\bilibili_downloader.py
```

## 補足

使用しているAPIは[こちら](https://github.com/SocialSisterYi/bilibili-API-collect)
