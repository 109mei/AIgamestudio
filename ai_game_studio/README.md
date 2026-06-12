# IDERIA Engine v1.1

自律型AIゲーム開発スタジオ「IDERIA Engine v1.1」へようこそ．本システムは，開発HUD（Pro Edition）と自己学習HUD（Study Edition）の2つの強力なツールから構成される，Pygameベース of AI自律型ゲーム開発統合シミュレータ環境です．

---

## 💻 1. 開発HUD（studio_pro_edition.exe）

6人のAI専門家エージェントが協調してゲーム開発のライフサイクルを自律的に進行するシステムです．

### エージェントバケツリレーフロー
1. **PM（Project Manager）**：ゲームの要件定義と仕様策定を行います．初期配置やオブジェクト情報を `map.json` にシリアライズする設計を行います．
2. **Designer（Game Designer）**：ゲーム性，操作方法，演出仕様を設計します．
3. **Programmer（Lead Pygame Dev）**：Pygameを用いた完全なPythonスクリプトコードを実装します．アセットは `Assets/Textures/ActiveAsset.png` からのロードを徹底します．
4. **QA（Quality Assurance）**：実装されたコードのテスト実行をトリガーし，例外が発生した場合はOllamaに自動修復を依頼します（最大3回）．
5. **VisualCritic（Art Director）**：UIレイアウト，配色，ビジュアルエフェクトの批評と改善提案を行います．
6. **Tester（Automation Tester）**：単体テストおよび動作確認のためのテストケースを策定します．

---

## 🌙 2. 自己学習HUD（study_mode.exe）

ゲーム開発に必要な最新技術，バグ回避手法，ライセンス，通信技術などを自律的または指示に基づいて学習・蓄積するエージェント環境です．

### 主な学習機能
- **自動学習モード**：最新のゲーム開発トレンド（GitHubやQiita等）を自動的にスクレイピングし，Ollamaで詳細な学習レポートを生成・蓄積します．
- **指示学習モード**：ユーザーが入力したテキスト（キーワードや解説）や指定したURL，PDF仕様書（例: RFC等のP2P通信仕様）を解析し，深い技術解説を生成します．
- **蓄積と学習フォルダ**：成果物やダウンロードされた仕様書PDFはすべて `LearnedAssets` フォルダに保存され，いつでも確認・活用できます．

---

## 🚀 3. v1.1 の新機能・強み

### ① ランゲージ切り替え機能
コントロールパネル上部のランゲージボタン（日本語・English）により，UIがリアルタイムに動的更新されます．英語モード時にはUIの切り替えのみならず，Ollamaへのシステムプロンプトや思考，最終成果物（仕様書，ソースコード，学習レポートなど）もすべて英語で自動生成されます．

### ② 軽量モード（Low-spec Mode）
ローカルのGPUリソースやOllamaがインストールされていないPC環境でも起動・実行できるよう，チェックボックス式の「軽量モード」を搭載しました．軽量モードが有効な場合は，重いAIモデルのロードやローカルGPU画像生成をスキップし，瞬時にダミー生成やPillow画像生成に切り替わるため，スペックに関係なくあらゆるPCで一瞬で動作します．

### ③ Ollama接続の超高速死活監視
Ollamaがインストールされているものの起動していない場合に，接続待ちでUI全体がフリーズするのを防ぐため，ポート（127.0.0.1:11434）への0.5秒タイムアウト死活確認を実装しました．接続が確認できない場合は，自動的に軽量シミュレータへと切り替わります．

---

## 🛠️ 推奨・必要環境

- **OS**：Windows 10/11
- **ランタイム**：Python 3.10以上，Ollama（llama3モデル推奨）
- **GPU（フル機能使用時）**：NVIDIA GeForce RTX 3070 / 4070 以上（VRAM 8GB以上推奨）

### 依存ライブラリのインストール
```bash
pip install customtkinter pillow ollama watchdog pygame pygame-menu
```
※ PyInstallerでビルドする際は， spec ファイルに定義された `excludes` 設定により，`torch` や `diffusers` などの巨大パッケージを除外して軽量・高速なシングルexe化が可能です．

---

## 📂 フォルダ構成
クリーンアップされた状態では以下の最小限のファイルで構成されます．
- `dist/`
  - `studio_pro_edition.exe`（ビルド済み開発HUD）
  - `study_mode.exe`（ビルド済み学習HUD）
- `studio_pro_edition.py`（開発HUDソースコード）
- `studio_pro_edition.spec`（開発HUDビルド定義）
- `studio_study_edition.py`（学習HUDソースコード）
- `study_mode.spec`（学習HUDビルド定義）
- `README.md`（本ファイル）

---

## 🚨 緊急時の操作
実行プロセスを緊急停止させたい場合は，HUD上の「🚨 作業強制終了 (ABORT STUDIO)」または「🛑 学習停止」を押下してください．バックグラウンド処理が安全に遮断され，GPUのVRAMキャッシュがパージ・解放されます．
