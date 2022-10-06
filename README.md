Bilibili Video and Mylist Downloader
====================================

# Features
ビリビリ動画に投稿された動画をダウンロードする.  
動画id (BVやAVから始まる)やマイリストid (mlから始まる)に対応. アカウントがある場合はその会員レベルに応じて高画質DLも可能.  
初回は [導入](#Installation) を参照してセットアップをし, 以降は[使い方](#Usage)を参考に.

## Todo List
- [x] 個別ダウンロード
- [x] マイリストの一括ダウンロード
- [x] 上書き保存をしない
- [ ] ダウンロード履歴管理
- [ ] FireFoxを必要としないログイン情報の取得


# Installation
2番以降はビリビリ動画のアカウントを所持しており高画質 (1080pや4Kなど)
1. releaseからzipファイルをダウンロードし解凍
2. [FireFox](https://www.mozilla.org/firefox/new/)をインストール
3. FireFoxにて [bilibili.com](https://www.bilibili.com) にログインする (数か月に一度ログインする必要がある)

# Usage
1. ダウンロードしたexeをダブルクリックすると動画idまたはマイリスidを求められるので入力.  
`https://www.bilibili.com/festival/VRSummerSuper?bvid=BV1wt4y1P78e` のようなURLのコピペからも自動的にidを抜粋してくれる.  
2. 画質値の入力が求められるので入力する.  
なお表示されているものでも元動画が対応していなかったりアカウントに権限がない場合は自動的に可能な画質でダウンロードされる.
3. 単体の動画であれば「Individual」、マイリスであればマイリス名のフォルダに動画保存される



# Build
## 1. Python環境を構築
仮想環境にてインストール.  Pythonのバージョンは3.7推奨. Pyenv+PipenvまたはPyenv+Poetry推奨. 
[参照](https://zenn.dev/hironobuu/articles/663ce389370210)
```bash
pipenv install --dev
```

## 2. Pythonをgccでビルドする
nuitkaを用いてPythonを必要としないバイナリファイルをビルドすることができる.
```ps
nuitka --follow-imports --onefile .\bilibili_downloader.py
```

# 補足
使用しているAPIは[こちら](https://github.com/SocialSisterYi/bilibili-API-collect)
