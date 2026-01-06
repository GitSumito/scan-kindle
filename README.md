# Kindle Scan for Mac

Kindle for Mac の自動スクリーンショット撮影 & PDF化ツールです。
macOS のネイティブ API (Quartz / Accessibility) を使用して、バックグラウンドでのページめくりとキャプチャを行います。
作成されたPDFは [NotebookLM](https://notebooklm.google.com/) などのRAGツールへのインポートに最適です。

## 特徴
- **Mac 専用**: macOS の Quartz Window Services を使用し、高速かつバックグラウンドでのキャプチャが可能です。
- **バックグラウンド動作**: Kindle アプリを最前面に出す必要がないため、スキャン中も他の作業（ブラウジングやコーディング）が可能です。
- **自動境界検出**: 本文領域を自動的に検出し、余白をトリミングします。
- **PDF 自動生成**: 撮影した連番画像を自動的に単一の PDF ファイルに変換します。

## 動作環境
- macOS (Apple Silicon / Intel)
- Python 3.10+
- Kindle for Mac

## インストール

1. リポジトリをクローンします。
2. 依存ライブラリをインストールします。


```bash
.venv/bin/pip install -r requirements.txt
```

> **注意**: 動作には「画面収録 (Screen Recording)」と「アクセシビリティ (Accessibility)」の権限が必要です。ターミナル（または実行するエディタ）に対して許可を与えてください。

## 使い方

### 1. Kindle のスキャン

Kindle アプリでスキャンしたい本を開き、**全画面表示ではない**状態でデスクトップに表示させておきます（裏に隠れていてもOKですが、最小化はしないでください）。

```bash
.venv/bin/python scan.py
```

- 自動的に Kindle ウィンドウを検出し、スキャンを開始します。
- 画像は `output/{ランダムな4桁ハッシュ}/` ディレクトリに保存されます（例: `output/a1b2/`）。
- ページめくりが止まると自動的に終了します。

### 2. PDF の作成

スキャンした画像を PDF に変換します。

```bash
.venv/bin/python pdf.py
```

- `output/` ディレクトリ内をスキャンし、まだ PDF 化されていないフォルダを自動的に処理します。
- 生成された PDF は `output/{ハッシュ}.pdf` として保存されます。

### 経過確認
生成された画像やPDFは `output/` ディレクトリに格納されますが、`.gitignore` に設定されているため、git 管理外となります。

## NotebookLM への活用
生成された PDF ファイルはテキストデータ（OCRは含まれませんが、画像ベースの認識能力が高いモデルなら可読）として、Google NotebookLM 等にアップロードして利用することができます。

## 構成
- `scan.py`: メインのキャプチャスクリプト
- `pdf.py`: 画像結合・PDF作成スクリプト

## ライセンス
MIT
