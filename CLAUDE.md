# CLAUDE.md

## プロジェクト概要

**claude-code-watcher** は、Claude Code に関する最新情報を自動収集し、GitHub Issues として登録する監視ツールです。

情報源は2つ:

1. **Anthropic Newsroom** (`https://www.anthropic.com/news`) — キーワードでフィルタリングしたニュース記事
2. **GitHub Releases** (`https://api.github.com/repos/anthropics/claude-code/releases`) — Claude Code の最新リリース

重複登録を防ぐため、`unique_key`（URL またはリリースタグ）で既存 Issue を検索してからのみ作成します。

## ディレクトリ構成

```text
claude-code-watcher/
├── scripts/
│   └── watch_claude_code.py   # メインスクリプト
├── .github/
│   └── workflows/
│       └── watch.yml          # GitHub Actions ワークフロー
├── requirements.txt           # Python 依存ライブラリ
└── CLAUDE.md
```

## 実行方法

### ローカル実行

```bash
pip install -r requirements.txt
GITHUB_TOKEN=<your_token> GITHUB_REPOSITORY=<owner/repo> python scripts/watch_claude_code.py
```

### 自動実行

GitHub Actions により **JST 毎朝 08:17（平日）** に自動実行されます（cron: `17 23 * * 0-4` UTC）。
手動実行は Actions タブの `workflow_dispatch` からも可能です。

## 依存ライブラリ

| パッケージ | バージョン | 用途 |
|---|---|---|
| `requests` | 2.32.3 | HTTP リクエスト |
| `beautifulsoup4` | 4.12.3 | Newsroom HTML のスクレイピング |

## 環境変数

| 変数名 | 説明 |
|---|---|
| `GITHUB_TOKEN` | GitHub API 認証トークン（`issues: write` 権限が必要） |
| `GITHUB_REPOSITORY` | 対象リポジトリ（例: `owner/repo`） |

## 監視キーワード

Newsroom スクレイピング時、以下のキーワードにマッチした記事のみ Issue 化します:

- `claude code`
- `agentic coding`
- `coding`
- `subagents`
- `hooks`
- `mcp`

## Issue フォーマット

作成される Issue には以下のセクションが含まれます:

- `source` — 情報源 (`anthropic-news` / `github-release`)
- `published` — 公開日時
- `url` — 元記事 URL
- `unique_key` — 重複検出用キー
- `summary` — 本文抜粋（リリースノート等）
- `triage` — 確認チェックリスト（読む / 試す / スキップ）

ラベル `claude-code-watch` が自動付与されます（存在しない場合は自動作成）。

## 注意事項

- Newsroom のスクレイピングはサイト構造の変更に影響されます。`a[href^="/news/"]` セレクタを使用しています。
- GitHub API のレート制限に注意してください（スクリプト内で Issue 検索も行うため）。
