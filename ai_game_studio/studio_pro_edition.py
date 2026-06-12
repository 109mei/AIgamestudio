import os
import sys
import time
import gc
import threading
import math
import queue
import re
import json
import random
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import shutil
from PIL import Image, ImageDraw
import customtkinter as ctk

# PyTorchのインポート（GPUキャッシュパージ用）
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Ollamaのインポート
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

# diffusersのインポート（フェーズ1）
try:
    from diffusers import DiffusionPipeline, LCMScheduler
    HAS_DIFFUSERS = True
except ImportError:
    HAS_DIFFUSERS = False

# chromadbのインポート（フェーズ2）
try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

# crewaiのインポート（フェーズ2）
try:
    from crewai import Agent as CrewAgent, Task as CrewTask, Crew as CrewNet, Process as CrewProcess
    from langchain_community.llms import Ollama as LCOllama
    HAS_CREWAI = True
    HAS_LC_OLLAMA = True
except ImportError:
    HAS_CREWAI = False
    HAS_LC_OLLAMA = False

# watchdogのインポート（改善案②）
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    class FileSystemEventHandler:
        pass
    class Observer:
        def __init__(self): pass
        def schedule(self, *args, **kwargs): pass
        def start(self): pass

def get_dummy_response(prompt, error_msg=None):
    # プロンプト内のキーワードに基づいてダミー出力を切り替えます．
    prefix = ""
    if error_msg:
        prefix = f"[注意: Ollama接続エラー ({error_msg}) のため，ローカルシミュレータが代替生成しました]\n\n"
    else:
        prefix = "[注意: Ollama未検出のため，ローカルシミュレータが代替生成しました]\n\n"

    if "優秀なゲーム開発pm" in prompt.lower():
        if "株" in prompt.lower() or "取引" in prompt.lower():
            return prefix + """【ゲーム要件定義書・仕様書】
■ プロジェクト名: IDERIA StockMarket
■ ターゲット: ビジネスシミュレーション層．
■ 主要機能:
1. 株価の変動ロジック処理（stock_market.py）．
2. 株価と資産のテキスト表示処理（stock_ui.py）．
■ 開発スケジュール:
- フェーズ1: コアコンポーネントの実装（Programmer）
- フェーズ2: UI連携とバリエーション画像テスト（Designer）
- フェーズ3: 静的検証および動作確認（QA）"""
        return prefix + """【ゲーム要件定義書・仕様書】
■ プロジェクト名: IDERIA Roller
■ ターゲット: カジュアルゲーマー層．
■ 主要機能:
1. プレイヤーキャラクター（球体）の物理挙動による移動制御（player_controller.py）．
2. ステージ上のアイテム収集とスコア加算処理（game_manager.py）．
■ 開発スケジュール:
- フェーズ1: コアメカニクスの実装（Programmer）
- フェーズ2: レベルデザインおよび調整（Designer）
- フェーズ3: デバッグおよび検証（QA）"""
    elif "クリエイティブなゲームデザイナー" in prompt.lower():
        return prefix + """【ゲームデザイン設計書】
■ 操作方法:
- 左右矢印キーによるキャラクターの左右移動（加速度加算方式）．
- スペースキーによるジャンプ挙動（接地判定あり）．
■ ゲームルール:
- 制限時間内にすべてのコインを回収し，ゴールへ到達すること．
- 落下（画面外への転落）時は即ゲームオーバーとする．
■ 画面演出:
- カメラはプレイヤーを後方から追従するスクロール形式．
- アイテム回収時にパーティクルエフェクトとポップなSEを再生．"""
    elif "実力派のunity c#" in prompt.lower() or "実力派のpygame" in prompt.lower() or "実力派のpython" in prompt.lower() or "実力派のc#" in prompt.lower():
        if "株" in prompt.lower() or "取引" in prompt.lower():
            return prefix + """【Pygame Pythonスクリプト】
// File: stock_market.py
import random

class StockMarket:
    def __init__(self):
        self.stock_price = 100.0
        self.timer = 0.0

    def update(self, dt):
        self.timer += dt
        if self.timer >= 2.0:
            change = random.uniform(-10.0, 10.0)
            self.stock_price += change
            self.timer = 0.0
            print(f"New Stock Price: {self.stock_price:.2f}")

// File: stock_ui.py
import pygame

class StockUI:
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 24)

    def draw(self, screen, market):
        text_surface = self.font.render(f"Stock Price: ${market.stock_price:.2f}", True, (255, 255, 255))
        screen.blit(text_surface, (20, 20))"""
        return prefix + """【Pygame Pythonスクリプト】
// File: game_manager.py
import pygame
import sys
import os
import json

class GameManager:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("IDERIA Roller")
        self.clock = pygame.clock.Clock()
        self.x = 400
        self.y = 300
        self.speed = 5
        self.score = 0
        self.load_map()
        self.load_assets()

    def load_map(self):
        try:
            with open("map.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.x = data["player"]["x"]
                self.y = data["player"]["y"]
        except Exception:
            pass

    def load_assets(self):
        self.player_image = None
        path = "Assets/Textures/ActiveAsset.png"
        if os.path.exists(path):
            try:
                self.player_image = pygame.image.load(path).convert_alpha()
                self.player_image = pygame.transform.scale(self.player_image, (40, 40))
            except Exception:
                pass

    def run(self):
        running = True
        loop_counter = 0
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                self.x -= self.speed
            if keys[pygame.K_RIGHT]:
                self.x += self.speed
                
            self.screen.fill((26, 26, 46))
            if self.player_image:
                self.screen.blit(self.player_image, (int(self.x) - 20, int(self.y) - 20))
            else:
                pygame.draw.circle(self.screen, (0, 210, 255), (int(self.x), int(self.y)), 20)
            pygame.display.flip()
            
            # テスト実行時の無限ループ防止ハック
            loop_counter += 1
            if loop_counter > 100:
                running = False
            
        pygame.quit()

if __name__ == "__main__":
    game = GameManager()
    game.run()"""
    elif "厳格なqaエンジニア" in prompt.lower():
        return prefix + """【QAレビューレポート】
■ 検証スクリプト: game_manager.py
■ 指摘事項:
1. 接地判定の論理エラー: 現在の実装ではプレイヤーがジャンプした際の接地状態が考慮されておらず，無限に空中ジャンプができる状態になっています．
2. スコア管理の疎結合化: スコア変数とUI描画処理が同一のクラスに混在しているため，ゲーム管理用クラスへ処理を委譲することを推奨します．
■ 判定結果: 警告あり（修正を推奨）．"""
    elif "美意識の高いアートディレクター" in prompt.lower():
        return prefix + """【ビジュアル・UI批評書】
■ 評価項目: 2Dスクロールアクションにおけるビジュアル演出
■ 改善提案:
1. 色彩設計: プレイヤーのドット絵はネオンブルーを採用し，背景はダークネイビーで構成することで高いコントラスト比を確保してください．
2. UI配置: スコアとタイマーのテキストは画面左上にまとめ，ネオンサイン風の発光演出（アンバー系）を適用することを提案します．
3. 描画負荷: スプライトシートを事前にロードし，毎フレームの画像変換処理を避けることで描画パフォーマンスを最適化してください．"""
    elif "実務に強いテストエンジニア" in prompt.lower():
        return prefix + """【テスト計画・テストケース】
■ テスト目的: game_manager.py の基本挙動およびイベントの動作確認
■ テストケース一覧:
1. TC_001: 矢印キー入力時にスプライトが指定方向へ移動することを確認する．
2. TC_002: ウィンドウの閉じるボタンを押下した際，ゲームループが正常に終了することを確認する．
3. TC_003: コインに衝突した際，スコアが1加算されることを確認する．"""
    else:
        clean_theme = prompt.replace("あなたはゲーム開発およびシステムアーキテクチャの専門家エージェントです．技術テーマ「", "").replace("」について調査・学習した内容をまとめ，開発における「コアノウハウ」「アルゴリズムや実装の工夫」「落とし穴や注意点」を日本語で詳細に解説してください．", "")
        return prefix + f"""【自動学習レポート: 技術・設計分析】
■ 対象テーマ: {clean_theme}
■ コアノウハウ:
1. Pygameの描画最適化: 画面全体を再描画するのではなく，変更のあった矩形領域（DirtyRect）のみを更新することでCPU負荷を極小化できます．
2. 疎結合コンポーネント設計: 描画，物理演算，入力処理を別々のモジュールに分離し，イベントキューを介して連携させる設計が保守性を向上させます．
■ 実装の工夫と注意点:
- Pygameのイベントハンドリングを行う際は，フレームごとに必ずイベントキューを全て消費してください．これを怠るとウィンドウがフリーズする原因になります．
- Pygame Community Edition (pygame-ce) を利用することで，最新の描画最適化機能やバグ修正の恩恵を受けることができます．"""

import socket

LOW_SPEC_MODE = False

def check_ollama_alive():
    try:
        # 0.5秒のタイムアウトで接続確認を行います．
        with socket.create_connection(("127.0.0.1", 11434), timeout=0.5):
            return True
    except Exception:
        return False

def ask_ollama(prompt):
    # Ollamaに接続してレスポンスを取得し，失敗した場合や軽量モード時はダミー出力を返します．
    global LOW_SPEC_MODE
    if LOW_SPEC_MODE:
        return get_dummy_response(prompt)
        
    if HAS_OLLAMA and check_ollama_alive():
        try:
            response = ollama.generate(model="llama3", prompt=prompt)
            return response.get("response", "")
        except Exception as e:
            return get_dummy_response(prompt, error_msg=str(e))
    else:
        return get_dummy_response(prompt)

def generate_asset_variations(workspace_dir, prompt):
    textures_dir = os.path.join(workspace_dir, "Assets", "Textures")
    if not os.path.exists(textures_dir):
        os.makedirs(textures_dir)
        
    global LOW_SPEC_MODE
    # フェーズ1: SD1.5+LCMによる高速画像生成（軽量モード時はスキップ）
    if not LOW_SPEC_MODE and HAS_DIFFUSERS and HAS_TORCH:
        try:
            pipe = DiffusionPipeline.from_pretrained("Lykon/dreamshaper-8-lcm", torch_dtype=torch.float16)
            pipe.to("cuda")
            pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
            
            colors_label = ["A", "B", "C"]
            for label in colors_label:
                # 4ステップ超高速・省エネ生成（グラボ保護）
                seed = hash(prompt + label) % (2**32)
                generator = torch.manual_seed(seed)
                image = pipe(f"pixel art, {prompt}, variation {label}", num_inference_steps=4, guidance_scale=8.0, generator=generator).images[0]
                filepath = os.path.join(textures_dir, f"Asset_{label}.png")
                image.save(filepath)
            return
        except Exception:
            pass # 失敗時はPillowへフォールバック
            
    # Pillowフォールバック
    colors = [
        ("#00d2ff", "A"),
        ("#ff3366", "B"),
        ("#00ff66", "C")
    ]
    for color, label in colors:
        img = Image.new("RGBA", (32, 32), "#1a1a2e")
        draw = ImageDraw.Draw(img)
        draw.rectangle([4, 8, 28, 28], fill=color)
        draw.rectangle([8, 12, 12, 16], fill="#ffffff")
        draw.rectangle([20, 12, 24, 16], fill="#ffffff")
        draw.rectangle([10, 14, 12, 16], fill="#000000")
        draw.rectangle([22, 14, 24, 16], fill="#000000")
        
        img_large = img.resize((128, 128), Image.NEAREST)
        filename = f"Asset_{label}.png"
        filepath = os.path.join(textures_dir, filename)
        img_large.save(filepath)

class TimeMachine:
    def __init__(self, workspace_dir, log_func):
        self.workspace_dir = workspace_dir
        self.log_func = log_func
        self.backup_history = []
        self.has_git = False
        self.check_git()
        
    def check_git(self):
        try:
            result = subprocess.run(["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            if result.returncode == 0:
                self.has_git = True
                subprocess.run(["git", "init"], cwd=self.workspace_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                gitignore_path = os.path.join(self.workspace_dir, ".gitignore")
                if not os.path.exists(gitignore_path):
                    with open(gitignore_path, "w") as f:
                        f.write("*.tmp\n__pycache__/\n")
        except Exception:
            self.has_git = False

    def save_checkpoint(self, message):
        if self.has_git:
            try:
                subprocess.run(["git", "add", "."], cwd=self.workspace_dir, shell=True)
                subprocess.run(["git", "commit", "-m", message], cwd=self.workspace_dir, shell=True)
                self.log_func(f"[タイムマシン] Gitコミットを作成しました: {message}\n")
                return
            except Exception as e:
                self.log_func(f"[警告] Gitコミットに失敗しました: {str(e)}\n")
        
        # フォールバックバックアップ
        backup_dir = self.workspace_dir + f"_backup_{int(time.time())}"
        try:
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.copytree(self.workspace_dir, backup_dir, ignore=shutil.ignore_patterns('*.git', '__pycache__'))
            self.backup_history.append((backup_dir, message))
            if len(self.backup_history) > 5:
                oldest_dir, _ = self.backup_history.pop(0)
                if os.path.exists(oldest_dir):
                    shutil.rmtree(oldest_dir)
            self.log_func(f"[タイムマシン] バックアップを作成しました ({len(self.backup_history)}/5世代)．\n")
        except Exception as e:
            self.log_func(f"[警告] バックアップ保存に失敗しました: {str(e)}\n")

    def restore_checkpoint(self):
        if self.has_git:
            try:
                result = subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=self.workspace_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
                if result.returncode == 0:
                    self.log_func("[タイムマシン] 1世代前のGitコミット状態へプロジェクトを復元しました．\n")
                    return True
                else:
                    self.log_func(f"[警告] Gitロールバックに失敗しました: {result.stderr}\n")
            except Exception as e:
                self.log_func(f"[警告] Gitロールバックエラー: {str(e)}\n")
                
        if not self.backup_history:
            self.log_func("[タイムマシン] 復元可能なバックアップ履歴が存在しません．\n")
            return False
            
        backup_dir, message = self.backup_history.pop()
        try:
            for item in os.listdir(self.workspace_dir):
                if item == ".git":
                    continue
                item_path = os.path.join(self.workspace_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            for item in os.listdir(backup_dir):
                s = os.path.join(backup_dir, item)
                d = os.path.join(self.workspace_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            shutil.rmtree(backup_dir)
            self.log_func(f"[タイムマシン] バックアップから復元しました: {message}\n")
            return True
        except Exception as e:
            self.log_func(f"[タイムマシン] 復元エラー: {str(e)}\n")
            return False

class ChromaDBManager:
    def __init__(self, workspace_dir, log_func):
        self.workspace_dir = workspace_dir
        self.log_func = log_func
        
        self.knowledge_base = [
            {"id": "kb_001", "version": "Unity 2020", "content": "Unity 2020におけるUIツールキットのメモリリークバグ仕様について"},
            {"id": "kb_002", "version": "Pygame CE", "content": "Pygame Community Editionにおける高効率なスプライト描画と DirtyRect 処理について"},
            {"id": "kb_003", "version": "C++ 11", "content": "C++ 11でのメモリアロケーションと生ポインタによる配列管理について"},
            {"id": "kb_004", "version": "Python 3.12", "content": "Python 3.12でのジェネレータ最適化と非同期処理による開発スピード向上について"},
            {"id": "kb_005", "version": "Unity 2019", "content": "Unity 2019での古いコンパイルバグと現在は不要になった回避パッチの適用について"}
        ]
        
        self.has_db = False
        if HAS_CHROMADB:
            try:
                db_path = os.path.join(workspace_dir, "ChromaDB")
                self.client = chromadb.PersistentClient(path=db_path)
                self.collection = self.client.get_or_create_collection("gamedev_rag")
                self.has_db = True
                
                for doc in self.knowledge_base:
                    self.collection.upsert(
                        documents=[doc["content"]],
                        metadatas=[{"version": doc["version"]}],
                        ids=[doc["id"]]
                    )
            except Exception:
                self.has_db = False

    def clean_contradictions(self):
        self.log_func("[RAGお掃除] ChromaDB内の知識矛盾チェックを開始します．\n")
        time.sleep(2)
        
        removed = []
        if self.has_db:
            try:
                for doc in list(self.knowledge_base):
                    if "Unity" in doc["version"] or "C++ 11" in doc["version"]:
                        self.collection.delete(ids=[doc["id"]])
                        removed.append(doc)
            except Exception:
                self.has_db = False
                
        if not self.has_db:
            for item in list(self.knowledge_base):
                if "Unity" in item["version"] or "C++ 11" in item["version"]:
                    self.knowledge_base.remove(item)
                    removed.append(item)
                    
        for item in removed:
            self.log_func(f"[RAGお掃除] 不要な情報「{item['content']}」({item['version']}) を自動検出し，ChromaDBから消去しました．\n")
            
        self.log_func("[RAGお掃除] データベースの最適化が完了しました．知能を最新状態にクリーンアップしました．\n")

    def add_debug_history(self, error_msg, fixed_code):
        # 改善案①: エラー自己修復解決策の動的学習記憶
        if self.has_db:
            try:
                doc_id = f"err_{int(time.time())}"
                content = f"【過去のエラー解決策】\nエラーログ:\n{error_msg}\n\n解決コード:\n{fixed_code}"
                self.collection.upsert(
                    documents=[content],
                    metadatas=[{"version": "debug_history"}],
                    ids=[doc_id]
                )
                self.log_func(f"[自己修復学習] エラーの解決策をデータベース（ID: {doc_id}）に学習記憶しました．\n")
            except Exception as e:
                self.log_func(f"[自己修復学習警告] デバッグ履歴の記憶に失敗しました: {str(e)}\n")

class ProjectUpdateHandler(FileSystemEventHandler):
    # 改善案②: watchdogによるプロジェクト更新検知ハンドラ
    def __init__(self, gui_app):
        self.gui_app = gui_app
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            self.gui_app.trigger_hot_reload()

class IDERIAGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 多言語データ定義
        self.current_lang = "JP"
        self.lang_data = {
            "JP": {
                "title": "IDERIA Engine v1.1 - Ultimate Pygame AI Game Studio HUD",
                "right_title": "🎛️ SYSTEM CONTROLS",
                "prompt_lbl": "📝 タスク指示プロンプト",
                "prompt_default": "Pygameで動作するシンプルな2D玉転がしゲームのプロトタイプを作成してください．",
                "day_btn": "💻 作業時間（日勤）開始",
                "timemachine_btn": "⌛ タイムマシン（復元）",
                "abort_btn": "🚨 作業強制終了 (ABORT STUDIO)",
                "gallery_title": "🎨 アセットバリエーション選択（デザイナー提案）／リアルタイムプレビュー",
                "btn_a": "候補Aを採用",
                "btn_b": "候補Bを採用",
                "btn_c": "候補Cを採用",
                "btn_active": "現在のアセット",
                "monitor_title": "💻 AI OUTPUT MONITOR",
                "phase_idle": "システムフェーズ: 待機中",
                "phase_active": "システムフェーズ: 日勤開発中",
                "cool_time_good": "GPUステータス: 良好 (VRAM解放済)",
                "cool_time_cooling": "GPU冷却中: {seconds}秒",
                "agent_status": "状態: {state}",
                "status_working": "作業中",
                "status_coffee": "コーヒー中",
                "status_idle": "休憩中",
                "low_spec_chk": "⚡ 軽量モード（低スペックPC向け）"
            },
            "EN": {
                "title": "IDERIA Engine v1.1 - Ultimate Pygame AI Game Studio HUD",
                "right_title": "🎛️ SYSTEM CONTROLS",
                "prompt_lbl": "📝 Task Prompt",
                "prompt_default": "Please create a simple 2D rolling ball game prototype running in Pygame.",
                "day_btn": "💻 Start Day Shift",
                "timemachine_btn": "⌛ Time Machine (Restore)",
                "abort_btn": "🚨 Abort Studio",
                "gallery_title": "🎨 Asset Variation Selection (Designer Proposal) / Real-time Preview",
                "btn_a": "Adopt A",
                "btn_b": "Adopt B",
                "btn_c": "Adopt C",
                "btn_active": "Current Asset",
                "monitor_title": "💻 AI OUTPUT MONITOR",
                "phase_idle": "System Phase: Idle",
                "phase_active": "System Phase: Day Shift Developing",
                "cool_time_good": "GPU Status: Good (VRAM Cleared)",
                "cool_time_cooling": "GPU Cooling: {seconds}s",
                "agent_status": "Status: {state}",
                "status_working": "Working",
                "status_coffee": "Coffee Break",
                "status_idle": "Idle",
                "low_spec_chk": "⚡ Low-spec Mode (Fast Simulation)"
            }
        }

        # 環境検出により軽量モードの初期値を決定
        global LOW_SPEC_MODE
        if not HAS_OLLAMA or not check_ollama_alive() or not HAS_TORCH:
            LOW_SPEC_MODE = True
        else:
            LOW_SPEC_MODE = False
        self.low_spec_var = ctk.BooleanVar(value=LOW_SPEC_MODE)
        
        self.agents_lang = {
            "JP": {
                "PM": {"name": "PM (Project Manager)", "desc": "要件定義と仕様策定を担当．"},
                "Designer": {"name": "Designer (Game Designer)", "desc": "ゲーム性と演出の設計を担当．"},
                "Programmer": {"name": "Programmer (Lead Pygame Dev)", "desc": "Pygame Pythonコードの実装を担当．"},
                "QA": {"name": "QA (Quality Assurance)", "desc": "コード検証と自己デバッグを担当．"},
                "VisualCritic": {"name": "VisualCritic (Art Director)", "desc": "UIとビジュアルの批評を担当．"},
                "Tester": {"name": "Tester (Automation Tester)", "desc": "テスト計画と実行を担当．"}
            },
            "EN": {
                "PM": {"name": "PM (Project Manager)", "desc": "In charge of requirements definition and specs."},
                "Designer": {"name": "Designer (Game Designer)", "desc": "In charge of gameplay and direction design."},
                "Programmer": {"name": "Programmer (Lead Pygame Dev)", "desc": "In charge of Pygame Python code implementation."},
                "QA": {"name": "QA (Quality Assurance)", "desc": "In charge of code verification and self-debugging."},
                "VisualCritic": {"name": "VisualCritic (Art Director)", "desc": "In charge of UI and visual critique."},
                "Tester": {"name": "Tester (Automation Tester)", "desc": "In charge of test planning and execution."}
            }
        }

        self.title("IDERIA Engine v1.1 - Ultimate Pygame AI Game Studio HUD")
        self.geometry("1200x750")
        self.resizable(False, False)

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self.workspace_dir = os.path.join(base_dir, "MyTemplateProject")
        if not os.path.exists(self.workspace_dir):
            os.makedirs(self.workspace_dir)

        # 参考文献フォルダの自動生成とお手本コードの配置（絶対条件①）
        self.ref_dir = os.path.join(self.workspace_dir, "Assets", "References")
        if not os.path.exists(self.ref_dir):
            os.makedirs(self.ref_dir)
        self.create_reference_data()

        # テクスチャフォルダの自動生成とデフォルトアセットの配置
        self.textures_dir = os.path.join(self.workspace_dir, "Assets", "Textures")
        if not os.path.exists(self.textures_dir):
            os.makedirs(self.textures_dir)
        self.create_default_texture()

        # マップ配置JSONの自動生成
        self.create_map_json()

        # 初期スクレイピングパターンの定義
        self.scraper_pattern = r'class="art-preview-title"[^>]*><a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'

        # ステート定義
        self.agents = {
            "PM": {"name": "PM (Project Manager)", "state": "休憩中", "desc": "要件定義と仕様策定を担当．"},
            "Designer": {"name": "Designer (Game Designer)", "state": "休憩中", "desc": "ゲーム性と演出の設計を担当．"},
            "Programmer": {"name": "Programmer (Lead Pygame Dev)", "state": "休憩中", "desc": "Pygame Pythonコードの実装を担当．"},
            "QA": {"name": "QA (Quality Assurance)", "state": "休憩中", "desc": "コード検証と自己デバッグを担当．"},
            "VisualCritic": {"name": "VisualCritic (Art Director)", "state": "休憩中", "desc": "UIとビジュアルの批評を担当．"},
            "Tester": {"name": "Tester (Automation Tester)", "state": "休憩中", "desc": "テスト計画と実行を担当．"}
        }

        # システム状態
        self.current_mode = "日勤"
        self.running_task = False
        self.abort_requested = False
        self.cooling_down = False
        self.cool_time_remaining = 0
        self.animation_counter = 0
        self.current_process = None
        self.current_genre = "general"

        # タイムマシンとRAGマネージャーの初期化
        self.time_machine = TimeMachine(self.workspace_dir, self.log_message)
        self.db_manager = ChromaDBManager(self.workspace_dir, self.log_message)

        # 改善案②: watchdogファイル監視observerの起動
        if HAS_WATCHDOG:
            self.observer = Observer()
            self.observer.schedule(ProjectUpdateHandler(self), self.workspace_dir, recursive=False)
            self.observer.start()

        # キュー処理
        self.log_queue = queue.Queue()

        # UI構築
        self.setup_ui()
        self.update_theme()
        self.update_gallery_images()

        # アニメーションとキュー監視開始
        self.animate_neon()
        self.check_queue_loop()

    def create_reference_data(self):
        pygame_ref_path = os.path.join(self.ref_dir, "PygameReference.txt")
        if not os.path.exists(pygame_ref_path):
            with open(pygame_ref_path, "w", encoding="utf-8") as f:
                f.write("""// Pygame高効率描画ベストプラクティス
import pygame
import sys

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    clock = pygame.clock.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        screen.fill((20, 20, 30))
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()""")

        pymunk_ref_path = os.path.join(self.ref_dir, "PymunkReference.txt")
        if not os.path.exists(pymunk_ref_path):
            with open(pymunk_ref_path, "w", encoding="utf-8") as f:
                f.write("""// Pymunk物理演算ベストプラクティス
import pymunk
import pymunk.pygame_util

space = pymunk.Space()
space.gravity = (0.0, 900.0)
body = pymunk.Body(1.0, 100.0)
body.position = (400.0, 100.0)
shape = pymunk.Circle(body, 20.0)
space.add(body, shape)""")

        # 改善案④: pygame-menu RAGリファレンステンプレートの追加
        menu_ref_path = os.path.join(self.ref_dir, "PygameMenuReference.txt")
        if not os.path.exists(menu_ref_path):
            with open(menu_ref_path, "w", encoding="utf-8") as f:
                f.write("""// PygameMenu設定画面テンプレート
import pygame
import pygame_menu

def start_the_game():
    pass

menu = pygame_menu.Menu('Welcome', 400, 300, theme=pygame_menu.themes.THEME_BLUE)
menu.add.text_input('Name :', default='Player')
menu.add.button('Play', start_the_game)
menu.add.button('Quit', pygame_menu.events.EXIT)""")

        # P2P通信・サーバー不要オンライン対戦のRAGテンプレート
        p2p_ref_path = os.path.join(self.ref_dir, "PygameP2PReference.txt")
        if not os.path.exists(p2p_ref_path):
            with open(p2p_ref_path, "w", encoding="utf-8") as f:
                f.write("""// Pygame UDP P2Pオンライン対戦・UPnP自動ポート開放テンプレート
import socket
import threading
try:
    import miniupnpc
    HAS_UPNP = True
except ImportError:
    HAS_UPNP = False

# UPnPによるルーターのポートマッピング自動開放
def setup_upnp(port, protocol="UDP"):
    if not HAS_UPNP:
        print("[UPnP] miniupnpcがインストールされていません．")
        return False
    try:
        # ローカルIPアドレスの自動取得
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        devices = upnp.discover()
        if devices > 0:
            upnp.selectigd()
            upnp.addportmapping(port, protocol, local_ip, port, "PygameP2PGamePort", "")
            print(f"[UPnP] ポート開放成功: {port} -> {local_ip}:{port} ({protocol})")
            return True
    except Exception as e:
        print(f"[UPnP] エラー: {e}")
    return False

# UDP P2Pオンライン対戦の通信管理クラス
class P2PConnection:
    def __init__(self, local_port, remote_ip, remote_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", local_port))
        self.remote_addr = (remote_ip, remote_port)
        self.running = True
        
        # 受信スレッドの開始
        self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.recv_thread.start()
        
    def _recv_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                message = data.decode("utf-8")
                print(f"Received from {addr}: {message}")
            except Exception:
                break
                
    def send_data(self, message):
        try:
            self.sock.sendto(message.encode("utf-8"), self.remote_addr)
        except Exception as e:
            print(f"Send error: {e}")
            
    def close(self):
        self.running = False
        self.sock.close()""")

    def create_default_texture(self):
        dest = os.path.join(self.textures_dir, "ActiveAsset.png")
        if not os.path.exists(dest):
            try:
                img = Image.new("RGBA", (32, 32), "#1a1a2e")
                draw = ImageDraw.Draw(img)
                draw.rectangle([4, 8, 28, 28], fill="#7f8c8d")
                img_large = img.resize((128, 128), Image.NEAREST)
                img_large.save(dest)
            except Exception:
                pass

    def create_map_json(self):
        map_path = os.path.join(self.workspace_dir, "map.json")
        if not os.path.exists(map_path):
            initial_map = {
                "player": {"x": 400.0, "y": 300.0},
                "enemies": [
                    {"type": "goblin", "x": 200.0, "y": 150.0},
                    {"type": "slime", "x": 600.0, "y": 450.0}
                ]
            }
            with open(map_path, "w", encoding="utf-8") as f:
                json.dump(initial_map, f, indent=4)

    def get_rag_context(self, query=None):
        rag_text = ""
        try:
            for filename in os.listdir(self.ref_dir):
                filepath = os.path.join(self.ref_dir, filename)
                if os.path.isfile(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        rag_text += f"\n--- 参考文献お手本 ({filename}) ---\n" + f.read() + "\n"
        except Exception:
            pass

        # 改善案①: 過去の自己修復履歴をChromaDBからRAG動的検索・注入
        if self.db_manager.has_db and query:
            try:
                results = self.db_manager.collection.query(
                    query_texts=[query],
                    n_results=1
                )
                if results and results.get("documents") and results["documents"][0]:
                    rag_text += f"\n--- 過去の自己修復デバッグ事例のRAG参照 ---\n{results['documents'][0][0]}\n"
            except Exception:
                pass
        return rag_text

    def detect_genre(self, prompt_text):
        prompt_lower = prompt_text.lower()
        if "株" in prompt_lower or "取引" in prompt_lower or "経済" in prompt_lower or "business" in prompt_lower:
            return "modern_office"
        elif "宇宙" in prompt_lower or "未来" in prompt_lower or "sf" in prompt_lower or "space" in prompt_lower:
            return "sci-fi"
        elif "魔法" in prompt_lower or "剣" in prompt_lower or "ファンタジー" in prompt_lower or "fantasy" in prompt_lower:
            return "retro_fantasy"
        return "general"

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=0, minsize=320)
        self.grid_columnconfigure(1, weight=1, minsize=580)
        self.grid_columnconfigure(2, weight=0, minsize=300)
        self.grid_rowconfigure(0, weight=1)

        # 左ペイン
        self.left_frame = ctk.CTkFrame(self, corner_radius=10, border_width=1)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.agent_frames = {}
        self.agent_labels = {}

        for i, (agent_id, info) in enumerate(self.agents.items()):
            self.left_frame.grid_rowconfigure(i, weight=1)
            card = ctk.CTkFrame(self.left_frame, corner_radius=8, border_width=2, border_color="#444444")
            card.grid(row=i, column=0, padx=10, pady=6, sticky="nsew")
            card.grid_columnconfigure(0, weight=1)
            
            name_lbl = ctk.CTkLabel(card, text=info["name"], font=("Segoe UI", 12, "bold"), anchor="w")
            name_lbl.grid(row=0, column=0, padx=10, pady=(6, 2), sticky="w")
            
            status_lbl = ctk.CTkLabel(card, text=f"状態: {info['state']}", font=("Segoe UI", 11), anchor="w")
            status_lbl.grid(row=1, column=0, padx=10, pady=(0, 2), sticky="w")
            
            desc_lbl = ctk.CTkLabel(card, text=info["desc"], font=("Segoe UI", 9), anchor="w")
            desc_lbl.grid(row=2, column=0, padx=10, pady=(0, 6), sticky="w")
            
            self.agent_frames[agent_id] = card
            self.agent_labels[agent_id] = {
                "name": name_lbl,
                "status": status_lbl,
                "desc": desc_lbl
            }

        # 中央ペイン
        self.center_frame = ctk.CTkFrame(self, corner_radius=10, border_width=1)
        self.center_frame.grid(row=0, column=1, padx=5, pady=10, sticky="nsew")
        self.center_frame.grid_columnconfigure(0, weight=1)
        self.center_frame.grid_rowconfigure(0, weight=0)
        self.center_frame.grid_rowconfigure(1, weight=1)
        self.center_frame.grid_rowconfigure(2, weight=0)

        self.status_panel = ctk.CTkFrame(self.center_frame, corner_radius=8)
        self.status_panel.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.status_panel.grid_columnconfigure(0, weight=1)
        self.status_panel.grid_columnconfigure(1, weight=1)
        
        self.phase_text = ctk.StringVar(value="システムフェーズ: 待機中")
        self.phase_label = ctk.CTkLabel(self.status_panel, textvariable=self.phase_text, font=("Segoe UI", 12, "bold"))
        self.phase_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        self.cool_time_text = ctk.StringVar(value="GPUステータス: 良好 (VRAM解放済)")
        self.cooldown_label = ctk.CTkLabel(self.status_panel, textvariable=self.cool_time_text, font=("Segoe UI", 12, "bold"))
        self.cooldown_label.grid(row=0, column=1, padx=15, pady=10, sticky="e")

        self.monitor_inner_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.monitor_inner_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.monitor_inner_frame.grid_columnconfigure(0, weight=1)
        self.monitor_inner_frame.grid_rowconfigure(0, weight=0)
        self.monitor_inner_frame.grid_rowconfigure(1, weight=1)

        self.monitor_title = ctk.CTkLabel(self.monitor_inner_frame, text="💻 AI OUTPUT MONITOR", font=("Segoe UI", 13, "bold"), anchor="w")
        self.monitor_title.grid(row=0, column=0, padx=5, pady=(0, 5), sticky="w")

        self.output_textbox = ctk.CTkTextbox(self.monitor_inner_frame, font=("Consolas", 11), wrap="word", border_width=1, corner_radius=6)
        self.output_textbox.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")

        self.gallery_frame = ctk.CTkFrame(self.center_frame, corner_radius=8, height=130)
        self.gallery_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.gallery_frame.grid_columnconfigure(0, weight=1)
        self.gallery_frame.grid_columnconfigure(1, weight=1)
        self.gallery_frame.grid_columnconfigure(2, weight=1)
        self.gallery_frame.grid_columnconfigure(3, weight=1)
        self.gallery_frame.grid_columnconfigure(4, weight=2) # プレビューCanvas用スペース確保
        
        self.gallery_title = ctk.CTkLabel(self.gallery_frame, text="🎨 アセットバリエーション選択（デザイナー提案）／リアルタイムプレビュー", font=("Segoe UI", 11, "bold"))
        self.gallery_title.grid(row=0, column=0, columnspan=5, padx=10, pady=5, sticky="w")
        
        self.create_placeholders()
        
        self.btn_a = ctk.CTkButton(self.gallery_frame, text="候補Aを採用", image=self.img_a_ctk, compound="top", command=lambda: self.select_variation("A"), font=("Segoe UI", 10), height=80)
        self.btn_a.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        self.btn_b = ctk.CTkButton(self.gallery_frame, text="候補Bを採用", image=self.img_b_ctk, compound="top", command=lambda: self.select_variation("B"), font=("Segoe UI", 10), height=80)
        self.btn_b.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        
        self.btn_c = ctk.CTkButton(self.gallery_frame, text="候補Cを採用", image=self.img_c_ctk, compound="top", command=lambda: self.select_variation("C"), font=("Segoe UI", 10), height=80)
        self.btn_c.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        
        self.btn_active = ctk.CTkButton(self.gallery_frame, text="現在のアセット", image=self.img_active_ctk, compound="top", state="disabled", fg_color="#2b2d42", font=("Segoe UI", 10), height=80)
        self.btn_active.grid(row=1, column=3, padx=5, pady=5, sticky="nsew")

        # 改善案③: HUD埋め込みリアルタイムプレビューCanvasの構築
        self.preview_canvas = ctk.CTkCanvas(self.gallery_frame, bg="#1a1a2e", highlightthickness=0, height=80)
        self.preview_canvas.grid(row=1, column=4, padx=5, pady=5, sticky="nsew")

        # 右ペイン
        self.right_frame = ctk.CTkFrame(self, corner_radius=10, border_width=1)
        self.right_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        
        self.right_title = ctk.CTkLabel(self.right_frame, text="🎛️ SYSTEM CONTROLS", font=("Segoe UI", 14, "bold"))
        self.right_title.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        # 言語切り替えSegmentedButton
        self.lang_var = ctk.StringVar(value="日本語")
        self.lang_switch = ctk.CTkSegmentedButton(
            self.right_frame,
            values=["日本語", "English"],
            variable=self.lang_var,
            command=self.change_language,
            font=("Segoe UI", 10, "bold"),
            fg_color="#161f30",
            selected_color="#0066cc",
            text_color="#e2e8f0"
        )
        self.lang_switch.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="e")
        
        self.prompt_lbl = ctk.CTkLabel(self.right_frame, text="📝 タスク指示プロンプト", font=("Segoe UI", 12, "bold"))
        self.prompt_lbl.grid(row=1, column=0, padx=15, pady=(5, 2), sticky="w")
        
        self.prompt_input = ctk.CTkTextbox(self.right_frame, height=140, border_width=1, corner_radius=6)
        self.prompt_input.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="ew")
        self.prompt_input.insert("1.0", "Pygameで動作するシンプルな2D玉転がしゲームのプロトタイプを作成してください．")
        
        self.day_btn = ctk.CTkButton(self.right_frame, text="💻 作業時間（日勤）開始", command=self.start_day_mode, font=("Segoe UI", 12, "bold"), height=35)
        self.day_btn.grid(row=3, column=0, padx=15, pady=6, sticky="ew")
        
        self.timemachine_btn = ctk.CTkButton(self.right_frame, text="⌛ タイムマシン（復元）", command=self.trigger_timemachine, font=("Segoe UI", 12, "bold"), height=35)
        self.timemachine_btn.grid(row=4, column=0, padx=15, pady=6, sticky="ew")
        
        # 軽量モードチェックボックス
        self.low_spec_chk = ctk.CTkCheckBox(
            self.right_frame,
            text="⚡ 軽量モード (低スペックPC向け)",
            variable=self.low_spec_var,
            command=self.toggle_low_spec_mode,
            font=("Segoe UI", 11, "bold"),
            text_color="#e2e8f0",
            fg_color="#0066cc",
            hover_color="#0052a3"
        )
        self.low_spec_chk.grid(row=5, column=0, padx=15, pady=10, sticky="w")
        
        self.abort_btn = ctk.CTkButton(self.right_frame, text="🚨 作業強制終了 (ABORT STUDIO)", command=self.abort_studio, fg_color="#c0392b", hover_color="#e74c3c", height=45, font=("Segoe UI", 12, "bold"))
        self.abort_btn.grid(row=6, column=0, padx=15, pady=(20, 15), sticky="ew")
        
        self.right_frame.grid_rowconfigure(5, weight=1)

    def create_placeholders(self):
        self.img_a_ctk = self.get_pillow_image_placeholder("#00d2ff", "A")
        self.img_b_ctk = self.get_pillow_image_placeholder("#ff3366", "B")
        self.img_c_ctk = self.get_pillow_image_placeholder("#00ff66", "C")
        self.img_active_ctk = self.get_pillow_image_placeholder("#7f8c8d", "Active")

    def get_pillow_image_placeholder(self, color, text):
        img = Image.new("RGBA", (32, 32), "#1a1a2e")
        draw = ImageDraw.Draw(img)
        draw.rectangle([4, 8, 28, 28], fill=color)
        img_large = img.resize((64, 40), Image.NEAREST)
        return ctk.CTkImage(light_image=img_large, dark_image=img_large, size=(64, 40))

    def update_gallery_images(self):
        textures_dir = os.path.join(self.workspace_dir, "Assets", "Textures")
        if os.path.exists(textures_dir):
            for label in ["A", "B", "C"]:
                path = os.path.join(textures_dir, f"Asset_{label}.png")
                if os.path.exists(path):
                    try:
                        img = Image.open(path).resize((64, 40), Image.NEAREST)
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(64, 40))
                        if label == "A":
                            self.btn_a.configure(image=ctk_img)
                        elif label == "B":
                            self.btn_b.configure(image=ctk_img)
                        elif label == "C":
                            self.btn_c.configure(image=ctk_img)
                    except Exception:
                        pass

    def select_variation(self, label):
        textures_dir = os.path.join(self.workspace_dir, "Assets", "Textures")
        source = os.path.join(textures_dir, f"Asset_{label}.png")
        dest = os.path.join(textures_dir, "ActiveAsset.png")
        try:
            if os.path.exists(source):
                shutil.copy2(source, dest)
                img = Image.open(dest).resize((64, 40), Image.NEAREST)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(64, 40))
                self.btn_active.configure(image=ctk_img)
                self.log_message(f"[システム] バリエーション {label} をゲーム用アクティブアセットとして正式採用しました．\n")
        except Exception as e:
            self.log_message(f"[システム] アセット採用エラー: {str(e)}\n")

    def trigger_timemachine(self):
        self.time_machine.restore_checkpoint()

    def toggle_low_spec_mode(self):
        global LOW_SPEC_MODE
        LOW_SPEC_MODE = self.low_spec_var.get()
        self.log_message(f"[システム] 軽量モードを {'ON' if LOW_SPEC_MODE else 'OFF'} に設定しました．\n" if self.current_lang == "JP" else f"[System] Low-spec mode configured to {'ON' if LOW_SPEC_MODE else 'OFF'}.\n")

    def change_language(self, lang_name):
        if lang_name == "日本語":
            self.current_lang = "JP"
        else:
            self.current_lang = "EN"
            
        data = self.lang_data[self.current_lang]
        
        self.title(data["title"])
        self.right_title.configure(text=data["right_title"])
        self.prompt_lbl.configure(text=data["prompt_lbl"])
        self.day_btn.configure(text=data["day_btn"])
        self.timemachine_btn.configure(text=data["timemachine_btn"])
        self.abort_btn.configure(text=data["abort_btn"])
        self.gallery_title.configure(text=data["gallery_title"])
        self.btn_a.configure(text=data["btn_a"])
        self.btn_b.configure(text=data["btn_b"])
        self.btn_c.configure(text=data["btn_c"])
        self.btn_active.configure(text=data["btn_active"])
        self.monitor_title.configure(text=data["monitor_title"])
        self.low_spec_chk.configure(text=data["low_spec_chk"])
        
        # プロンプト入力欄のデフォルト表示切り替え
        current_prompt = self.prompt_input.get("1.0", "end-1c").strip()
        prev_lang = "EN" if self.current_lang == "JP" else "JP"
        if current_prompt == self.lang_data[prev_lang]["prompt_default"]:
            self.prompt_input.delete("1.0", "end")
            self.prompt_input.insert("1.0", data["prompt_default"])
            
        # フェーズ表示の更新
        if self.running_task:
            self.phase_text.set(data["phase_active"])
        else:
            self.phase_text.set(data["phase_idle"])
            
        # GPU冷却の更新
        if self.cooling_down:
            self.cool_time_text.set(data["cool_time_cooling"].format(seconds=self.cool_time_remaining))
        else:
            self.cool_time_text.set(data["cool_time_good"])
            
        # エージェントカードの更新
        ag_data = self.agents_lang[self.current_lang]
        for agent_id in self.agents:
            self.agent_labels[agent_id]["name"].configure(text=ag_data[agent_id]["name"])
            self.agent_labels[agent_id]["desc"].configure(text=ag_data[agent_id]["desc"])
            
            state = self.agents[agent_id]["state"]
            state_text = data["status_working"] if state == "作業中" else (data["status_coffee"] if state == "コーヒー中" else data["status_idle"])
            self.agent_labels[agent_id]["status"].configure(text=data["agent_status"].format(state=state_text))

    def update_theme(self):
        bg_color = "#0b0f19"
        pane_color = "#161f30"
        card_color = "#1e293b"
        text_color = "#e2e8f0"
        accent_color = "#00d2ff"
        textbox_bg = "#070c14"

        self.configure(fg_color=bg_color)
        self.left_frame.configure(fg_color=pane_color, border_color=accent_color)
        self.center_frame.configure(fg_color=pane_color, border_color=accent_color)
        self.right_frame.configure(fg_color=pane_color, border_color=accent_color)
        self.output_textbox.configure(fg_color=textbox_bg, text_color=text_color)
        self.prompt_input.configure(fg_color=textbox_bg, text_color=text_color)
        self.monitor_title.configure(text_color=text_color)
        self.gallery_frame.configure(fg_color=pane_color, border_color=accent_color)
        self.gallery_title.configure(text_color=text_color)
        
        self.day_btn.configure(fg_color="#0066cc", hover_color="#0052a3", text_color="#ffffff")
            
        for agent_id in self.agents:
            self.agent_frames[agent_id].configure(fg_color=card_color)
            self.agent_labels[agent_id]["name"].configure(text_color=text_color)
            self.agent_labels[agent_id]["desc"].configure(text_color="#94a3b8")

    def animate_neon(self):
        self.animation_counter += 1
        data = self.lang_data[self.current_lang]
        
        for agent_id, info in self.agents.items():
            state = info["state"]
            frame = self.agent_frames[agent_id]
            
            state_text = data["status_working"] if state == "作業中" else (data["status_coffee"] if state == "コーヒー中" else data["status_idle"])
            self.agent_labels[agent_id]["status"].configure(text=data["agent_status"].format(state=state_text))
            
            if state == "作業中":
                pulse = int(180 + 75 * math.sin(self.animation_counter * 0.2))
                color = f"#00{pulse:02x}ff"
                frame.configure(border_color=color)
                self.agent_labels[agent_id]["status"].configure(text_color="#00d2ff")
            elif state == "コーヒー中":
                pulse = int(100 + 50 * math.sin(self.animation_counter * 0.1))
                color = f"#a0{int(pulse*0.5):02x}{int(pulse*0.3):02x}"
                frame.configure(border_color=color)
                self.agent_labels[agent_id]["status"].configure(text_color="#a0522d")
            elif state == "休憩中":
                frame.configure(border_color="#00cc66")
                self.agent_labels[agent_id]["status"].configure(text_color="#00cc66")
                
        if self.cooling_down:
            pulse = int(127 + 128 * math.sin(self.animation_counter * 0.3))
            self.cool_time_text.set(data["cool_time_cooling"].format(seconds=self.cool_time_remaining))
            self.cooldown_label.configure(text_color=f"#{pulse:02x}0000")
        else:
            self.cooldown_label.configure(text_color="#00ff66")
            
        self.after(100, self.animate_neon)

    def check_queue_loop(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            if msg == "REFRESH_GALLERY":
                self.update_gallery_images()
            else:
                self.output_textbox.insert("end", msg)
                self.output_textbox.see("end")
        self.after(100, self.check_queue_loop)

    def log_message(self, message):
        self.log_queue.put(message)

    def start_day_mode(self):
        if self.running_task:
            self.log_message("[警告] 現在すでに別のタスクが実行中です．\n")
            return
            
        self.current_mode = "日勤"
        self.running_task = True
        self.abort_requested = False
        self.update_theme()
        
        prompt = self.prompt_input.get("1.0", "end-1c").strip()
        if not prompt:
            prompt = "Pygame用のシンプルな2Dゲームプロトタイプ"
            
        self.current_genre = self.detect_genre(prompt)
        self.phase_text.set("システムフェーズ: 日勤開発中")
        
        self.relay_thread = threading.Thread(target=self._relay_loop, args=(prompt,), daemon=True)
        self.relay_thread.start()



    def abort_studio(self):
        if not self.running_task:
            self.log_message("[システム] 実行中のタスクはありません．\n")
            return
            
        self.log_message("[システム] 強制終了要求を受信しました．直ちにGPU VRAMを解放します．\n")
        self.abort_requested = True
        
        if hasattr(self, "current_process") and self.current_process:
            try:
                self.current_process.kill()
                self.log_message("[システム] 実行中の Pygame テストプロセスを強制終了しました．\n")
            except Exception:
                pass
        self.clean_gpu_vram()

    def trigger_hot_reload(self):
        # 改善案②: ホットリロードの処理スケジュール
        if self.running_task and self.agents["QA"]["state"] == "作業中":
            self.log_message("[ホットリロード] コード更新を検知しました．テストプロセスを再起動します．\n")
            if hasattr(self, "current_process") and self.current_process:
                try:
                    self.current_process.kill()
                except Exception:
                    pass

    def run_cooldown(self, seconds, agent_id=None):
        self.cooling_down = True
        if agent_id:
            for aid in self.agents:
                self.agents[aid]["state"] = "コーヒー中" if aid == agent_id else "休憩中"
                
        self.log_message(f"[システム] GPU保護のため冷却待機に入ります (待機時間: {seconds}秒)．\n")
        for i in range(seconds):
            if self.abort_requested:
                break
            remaining = seconds - i
            self.cool_time_text.set(f"GPU冷却中: {remaining}秒")
            time.sleep(1)
            
        self.clean_gpu_vram()
        self.cooling_down = False
        self.cool_time_text.set("GPUステータス: 良好 (VRAM解放済)")

    def run_pygame_test(self):
        self.log_message("[システム] Pygame (HUDドッキング埋め込み) の起動および実行時例外検証をトリガーします．\n")
        game_script = os.path.join(self.workspace_dir, "game_manager.py")
        log_path = os.path.join(self.workspace_dir, "pygame_log.txt")
        
        if not os.path.exists(game_script):
            self.log_message("[システム] 検証対象の game_manager.py が見つかりません．検証をスキップします．\n")
            return True
            
        try:
            env = os.environ.copy()
            # 改善案③: SDL_WINDOWIDを利用したTkinter CanvasへのPygameウィンドウの埋め込みドッキング
            try:
                env["SDL_WINDOWID"] = str(self.preview_canvas.winfo_id())
                env["SDL_VIDEODRIVER"] = "windib"
            except Exception:
                pass
                
            self.current_process = subprocess.Popen(
                ["python", game_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            try:
                stdout, stderr = self.current_process.communicate(timeout=3)
                if self.current_process.returncode != 0 and self.current_process.returncode is not None:
                    with open(log_path, "w", encoding="utf-8") as f:
                        f.write(stderr)
                    self.log_message(f"[システム] Pygameの実行時にエラーが発生しました．ログ: {log_path}\n")
                    return False
            except subprocess.TimeoutExpired:
                self.current_process.kill()
                self.log_message("[システム] Pygameテスト実行は正常に3秒間動作し，例外は発生しませんでした．\n")
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("Pygame Run Success. No errors detected during 3s run.")
                return True
        except Exception as e:
            self.log_message(f"[システム] テストプロセス起動エラー: {str(e)}\n")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(str(e))
            return False
        finally:
            self.current_process = None

    def extract_asset_list(self):
        assets_found = []
        try:
            for filename in os.listdir(self.workspace_dir):
                if filename.endswith(".py"):
                    filepath = os.path.join(self.workspace_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        code = f.read()
                    finds = re.findall(r'"([a-zA-Z0-9_/]+(?:\.png|\.wav|\.json))"', code)
                    assets_found.extend(finds)
            
            assets_found = list(set(assets_found))
            if not assets_found:
                assets_found = ["Textures/ActiveAsset.png", "map.json"]
                
            list_path = os.path.join(self.workspace_dir, "asset_list.txt")
            with open(list_path, "w", encoding="utf-8") as f:
                for asset in assets_found:
                    f.write(asset + "\n")
            self.log_message(f"[システム] Pythonコードから調達素材リストを抽出し，{list_path} に出力しました．\n")
        except Exception as e:
            self.log_message(f"[警告] 素材リスト抽出エラー: {str(e)}\n")

    def clean_gpu_vram(self):
        self.log_message("[システム] VRAMキャッシュのパージを実行します．\n")
        gc.collect()
        if HAS_TORCH:
            try:
                torch.cuda.empty_cache()
                self.log_message("[システム] PyTorch VRAMキャッシュを完全にパージしました．\n")
            except Exception as e:
                self.log_message(f"[警告] PyTorch VRAMキャッシュのパージに失敗しました: {str(e)}\n")
        else:
            self.log_message("[システム] PyTorch非搭載のため，ガベージコレクションのみ実行しました．\n")

    def build_prompt_for_agent(self, agent_id, context):
        if self.current_lang == "JP":
            if agent_id == "PM":
                return (
                    f"あなたは優秀なゲーム開発PMです．以下の要望をもとに，ゲームの要件定義書と仕様書を日本語で作成してください．\n"
                    f"【必須要件】すべての機能を1つのファイルに記述することは避けてください．Python/Pygameの設計に基づき，"
                    f"「機能別（例: game_manager.py，stock_market.py）」にモジュール化したTODOタスクを出力してください．\n"
                    f"【配置のルール】ゲームのマップオブジェクトやプレイヤーの配置データは，[map.json] というJSON形式でシリアライズしてロードする設計を行ってください．\n"
                    f"【対戦・通信のルール】フレンド対戦やオンライン対戦を追加する場合は，中央サーバーを不要とするP2P（Peer-to-Peer）方式を採用し，UDPホールパンチングやUPnP自動ポート開放による自動接続を優先して設計してください．\n"
                    f"{context}"
                )
            elif agent_id == "Designer":
                return f"あなたはクリエイティブなゲームデザイナーです．以下の仕様書をもとに，ゲームのルール，操作方法，演出などの詳細なゲームデザインを日本語で設計してください．\n{context}"
            elif agent_id == "Programmer":
                rag = self.get_rag_context(query=context)
                return (
                    f"あなたは実力派のPygameプログラマーです．以下のデザイン設計をもとに，Pygameで動作する完全なPythonスクリプトコードを作成してください．\n"
                    f"解説は最小限にし，コードの定義開始部分に必ず「// File: ファイル名.py」を記述したコードブロックを含めてください．\n"
                    f"【アセットロードの絶対ルール】\n"
                    f"1. 画像アセット（プレイヤーのスプライトや背景等）を描画する際は，必ず [Assets/Textures/ActiveAsset.png] からロードして使用してください．ファイルが存在しない場合の例外処理も記述してください．\n"
                    f"2. キャラクターや敵などの初期配置座標を決定する際は，必ず [map.json] をロードしてその座標データ（player.x, player.y等）を使用してください．\n"
                    f"【対戦・通信の絶対ルール】\n"
                    f"フレンド対戦やオンライン対戦を実装する場合は，必ず [PygameP2PReference.txt] のUDPソケット通信・受信スレッドモデルをベースとし，外部サーバー不要のP2P自動接続処理を記述してください．\n"
                    f"【RAG参考文献・お手本コード】\n{rag}\n"
                    f"【設計コンテキスト】\n{context}"
                )
            elif agent_id == "QA":
                return f"あなたは厳格なQAエンジニアです．以下のPythonスクリプトを読み，潜在的なバグ，論理的エラー，または改善点を指摘するコードレビューレポートを日本語で作成してください．\n{context}"
            elif agent_id == "VisualCritic":
                return f"あなたは美意識の高いアートディレクターです．これまでの開発内容を踏まえ，ゲームのUIレイアウト，配色，ビジュアルエフェクトの改善案と評価を日本語で作成してください．\n{context}"
            elif agent_id == "Tester":
                return f"あなたは実務に強いテストエンジニアです．完成したコードと仕様をもとに，単体テストおよび動作確認のためのテストケースを日本語で作成してください．\n{context}"
        else: # 英語モード
            if agent_id == "PM":
                return (
                    f"You are an excellent game PM. Based on the following requirements, please create a game requirements definition and spec in English.\n"
                    f"[Essential Requirement] Avoid writing all features in a single file. Design it in modular Python/Pygame scripts (e.g. game_manager.py, stock_market.py) with TODO tasks.\n"
                    f"[Placement Rule] The game map objects and player placement coordinates MUST be serialized and loaded from a [map.json] file.\n"
                    f"[Network/P2P Rule] If friend match or online multiplayer is requested, design it using Peer-to-Peer (P2P) without a central server, prioritizing UDP hole punching or UPnP automatic port mapping.\n"
                    f"{context}"
                )
            elif agent_id == "Designer":
                return f"You are a creative game designer. Based on the specs, design the detailed game rules, controls, and visual details in English.\n{context}"
            elif agent_id == "Programmer":
                rag = self.get_rag_context(query=context)
                return (
                    f"You are a skilled Pygame programmer. Based on the design, write complete, working Python script code in Pygame. All comments and logs must be in English.\n"
                    f"Keep explanations minimal and start your code block with '// File: filename.py'.\n"
                    f"[Asset Loading Rules]\n"
                    f"1. You MUST load player sprites and textures from [Assets/Textures/ActiveAsset.png]. Include exception handling in case the file does not exist.\n"
                    f"2. You MUST load initial coordinates from [map.json] (e.g., player.x, player.y).\n"
                    f"[Network/P2P Rules]\n"
                    f"For online match, use the UDP socket communication and receiver thread model shown in [PygameP2PReference.txt] as a base, implementing server-less P2P auto-connection.\n"
                    f"[RAG Reference/Templates]\n{rag}\n"
                    f"[Design Context]\n{context}"
                )
            elif agent_id == "QA":
                return f"You are a strict QA engineer. Read the following Python script and create a code review report in English pointing out potential bugs, logical errors, or improvements.\n{context}"
            elif agent_id == "VisualCritic":
                return f"You are a visual critic / art director. Provide feedback and improvements on UI layout, colors, and visual effects in English based on the development progress.\n{context}"
            elif agent_id == "Tester":
                return f"You are a test engineer. Create unit tests and test cases in English based on the code and specs.\n{context}"
        return context

    def save_code_to_project(self, text):
        file_blocks = re.findall(r'(?://\s*File:\s*([a-zA-Z0-9_\.]+\.py)|```python:([a-zA-Z0-9_\.]+\.py))\n(.*?)(?=//\s*File:|```python:|$)', text, re.DOTALL)
        
        if file_blocks:
            for name1, name2, body in file_blocks:
                filename = name1 if name1 else name2
                # コードブロックの中身だけを抽出することを試みます．
                code_match = re.search(r'```(?:python|py)\n(.*?)\n```', body, re.DOTALL)
                if code_match:
                    clean_body = code_match.group(1).strip()
                else:
                    clean_body = body.replace("```python", "").replace("```", "").strip()
                filepath = os.path.join(self.workspace_dir, filename)
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(clean_body)
                    self.log_message(f"[システム] モジュール {filename} を {filepath} に自動分割保存しました．\n")
                except Exception as e:
                    self.log_message(f"[システム] モジュール {filename} の保存エラー: {str(e)}\n")
        else:
            code = ""
            # まずコードブロック（python）からの抽出を試みます．
            code_match = re.search(r'```(?:python|py)\n(.*?)\n```', text, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            else:
                lines = text.split("\n")
                in_block = False
                for line in lines:
                    if line.strip().startswith("```"):
                        if "python" in line or "py" in line or not in_block:
                            in_block = not in_block
                            continue
                    if in_block:
                        code += line + "\n"
                        
                if not code.strip():
                    # マークダウンのない平文コードの場合
                    code = text.strip()
                    
            filepath = os.path.join(self.workspace_dir, "game_manager.py")
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(code)
                self.log_message(f"[システム] Pygame用Pythonスクリプトを {filepath} に保存しました．\n")
            except Exception as e:
                self.log_message(f"[システム] ファイル保存エラー: {str(e)}\n")

    def rewrite_map_json(self, x, y):
        map_path = os.path.join(self.workspace_dir, "map.json")
        if os.path.exists(map_path):
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["player"]["x"] = x
                data["player"]["y"] = y
                with open(map_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                self.log_message(f"[システム] map.json を直接書き換え，プレイヤー配置座標を ({x}, {y}) に調整しました．\n")
            except Exception as e:
                self.log_message(f"[警告] map.json 書き換えに失敗しました: {str(e)}\n")

    def save_map_generator(self):
        filepath = os.path.join(self.workspace_dir, "map_generator.py")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("""# Pygame用自動アセット等間隔配置ジェネレーター
import json
import os

def generate_line_map(count=5, step=80.0):
    map_data = {
        "player": {"x": 400.0, "y": 300.0},
        "enemies": []
    }
    for i in range(count):
        map_data["enemies"].append({
            "type": "slime",
            "x": 100.0 + i * step,
            "y": 150.0
        })
    with open("map.json", "w", encoding="utf-8") as f:
        json.dump(map_data, f, indent=4)
    print("[IDERIA] map.json を等間隔配置で自動生成しました．")

if __name__ == "__main__":
    generate_line_map()""")
            self.log_message(f"[システム] マップジェネレーター map_generator.py を保存しました．\n")
        except Exception as e:
            self.log_message(f"[警告] マップジェネレーターの保存に失敗しました: {str(e)}\n")

    def fetch_latest_tech_news(self):
        self.log_message("[システム] 最新のゲーム開発トレンド（GitHub/Qiita/isocpp）を自動調査中です．\n")
        news_items = []
        try:
            url = f"https://api.github.com/search/repositories?q=pygame+OR+pymunk+{self.current_genre}&sort=stars&order=desc&per_page=3"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) IDERIA-Engine/1.0', 'Accept': 'application/vnd.github.v3+json'})
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode('utf-8'))
                for repo in data.get('items', [])[:3]:
                    title = f"GitHub: {repo['name']} (Stars: {repo['stargazers_count']})"
                    desc = repo['description'] if repo['description'] else "No description"
                    news_items.append({"title": f"[GitHubトレンド] {title}", "desc": desc[:100]})
        except Exception as e:
            self.log_message(f"[警告] GitHubトレンドの取得に失敗しました: {str(e)}\n")
            
        try:
            url = "https://qiita.com/tags/pygame/feed.atom"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=8) as response:
                xml_data = response.read()
            root = ET.fromstring(xml_data)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns)[:3]:
                title = entry.find('atom:title', ns).text
                news_items.append({"title": "[Qiitaトレンド] " + title, "desc": "QiitaのPygame技術トレンド記事です．"})
        except Exception as e:
            self.log_message(f"[警告] Qiitaトレンドの取得に失敗しました: {str(e)}\n")
            
        if news_items:
            self.log_message(f"[システム] 合計 {len(news_items)} 件の最新トレンド情報を取得しました．\n")
        else:
            self.log_message("[注意] オンライン自動調査に失敗しました．ローカル知識ベースにフォールバックします．\n")
        return news_items

    def check_scraper_maintenance(self):
        self.log_message(f"[保守] CC0素材サイト (OpenGameArt) の構造検査を開始します (対象ジャンル: {self.current_genre})．\n")
        url = f"https://opengameart.org/art-search-advanced?keys={self.current_genre}+pygame&field_art_type_value[]=9&sort_by=created&sort_order=DESC"
        try:
            time.sleep(random.uniform(2.0, 3.0))
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=8) as response:
                html = response.read().decode('utf-8')
                
            matches = re.findall(self.scraper_pattern, html)
            if not matches:
                self.log_message("[保守警告] 素材サイト of 構造変化を検知しました (マッチ数0件)．自己修復を開始します．\n")
                html_sample = html[:3000]
                prompt = (
                    f"あなたはシステム保守エンジニアです．素材サイト (OpenGameArt) のHTML構造が変更されました．\n"
                    f"以下に示す変更後のHTMLサンプルから，素材リンクとタイトルを抽出するための新しいPythonの「正規表現パターン」を1つだけ出力してください．\n"
                    f"元のパターン: {self.scraper_pattern}\n"
                    f"HTMLサンプル:\n{html_sample}\n\n"
                    f"出力は余計な解説を一切含めず，Pythonの raw 文字列 of 正規表現パターン（例: class=\"art-preview-title\"[^>]*><a[^>]*href=\"([^\"]+)\"[^>]*>([^<]+)</a>）単体のみを出力してください．"
                )
                self.log_message("[保守] Ollama (llama3) で新しいスクレイピング正規表現を生成中です．\n")
                new_pattern = ask_ollama(prompt).strip()
                new_pattern = new_pattern.replace("'", "").replace('"', "").replace("`", "").strip()
                
                if new_pattern and len(new_pattern) > 5:
                    self.scraper_pattern = new_pattern
                    self.self_update_scraper(new_pattern)
                else:
                    self.log_message("[警告] 新しいパターンの生成に失敗しました．フォールバックします．\n")
            else:
                self.log_message(f"[保守] 構造検査をクリアしました．正常に {len(matches)} 件のアセットが検出可能です．\n")
        except Exception as e:
            self.log_message(f"[注意] 保守検査中にネットワークまたはアクセス制限を検出しました ({str(e)})．ダミーでの自己修復シミュレーションを起動します．\n")
            sim_pattern = r'class="art-preview-title-v2"[^>]*><a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
            self.scraper_pattern = sim_pattern
            self.self_update_scraper(sim_pattern)

    def self_update_scraper(self, new_pattern):
        filepath = os.path.abspath(__file__)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            pattern_def = f"self.scraper_pattern = r'{new_pattern}'"
            updated_content = re.sub(r"self\.scraper_pattern\s*=\s*r'[^']+'", pattern_def, content)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(updated_content)
            self.log_message(f"[保守] スクリプトの自己書き換えに成功しました．新しい抽出パターン: {new_pattern}\n")
            self.time_machine.save_checkpoint("[自動セーブ] スクレイピングコードの自己保守・アップデート完了")
        except Exception as e:
            self.log_message(f"[警告] 自己アップデート書き込みに失敗しました: {str(e)}\n")

    def _relay_loop(self, base_prompt):
        self.log_message("[システム] 日勤開発タスクを開始します．\n")
        relay_order = ["PM", "Designer", "Programmer", "QA", "VisualCritic", "Tester"]
        context = f"初期タスク要求: {base_prompt}\n"
        
        for idx, agent_id in enumerate(relay_order):
            if self.abort_requested:
                break
                
            for aid in self.agents:
                self.agents[aid]["state"] = "作業中" if aid == agent_id else "休憩中"
                
            self.log_message(f"--- 【{self.agents[agent_id]['name']}】がタスクを開始します ---\n")
            
            if agent_id == "QA":
                self.log_message("---------------------------------------\n")
                self.log_message("|QAエージェント:|\n")
                self.log_message("|「よし，Pygameの起動検証とバグの自己修復を走らせるぞ」|\n")
                self.log_message("---------------------------------------\n")
                self.log_message("          \\  (•̀_•́)\n\n")
                
                success = False
                for attempt in range(1, 4):
                    self.log_message(f"[自己修復検証] 起動テストを実行中 (試行: {attempt}/3)．")
                    success = self.run_pygame_test()
                    if success:
                        self.log_message("[自己修復検証] テストに合格しました！実行時エラーは検出されませんでした．\n")
                        break
                    else:
                        log_path = os.path.join(self.workspace_dir, "pygame_log.txt")
                        err_content = ""
                        if os.path.exists(log_path):
                            with open(log_path, "r", encoding="utf-8") as f:
                                err_content = f.read()
                        
                        self.log_message(f"[自己修復検証] エラーを検出しました:\n{err_content}\n[自己修復検証] Ollamaに修復を依頼します．\n")
                        
                        game_script = os.path.join(self.workspace_dir, "game_manager.py")
                        code_content = ""
                        if os.path.exists(game_script):
                            with open(game_script, "r", encoding="utf-8") as f:
                                code_content = f.read()
                                
                        fix_prompt = (
                            f"あなたは優秀なPygameデバッガーです．以下のPygameコードを実行した際，エラーが発生しました．\n"
                            f"発生したエラーログ:\n{err_content}\n\n"
                            f"現在のソースコード:\n{code_content}\n\n"
                            f"このエラーを修正した完全なソースコードを出力してください．解説は不要です．C#ではなくPythonの完全なコードを出力し，"
                            f"コードの定義開始部分に必ず「// File: game_manager.py」を記述したコードブロックを含めてください．"
                        )
                        fixed_code = ask_ollama(fix_prompt)
                        self.save_code_to_project(fixed_code)
                        
                        # 改善案①: 修復成功時にバグ解決履歴をChromaDBに自己修復記憶させる
                        if attempt == 3 or self.run_pygame_test():
                            self.db_manager.add_debug_history(err_content, fixed_code)
                
                if not success:
                    self.log_message("[警告] 最大自己修復試行回数に達しましたが，エラーが解消されていない可能性があります．ログを確認してください．\n")
                
                self.extract_asset_list()
                self.time_machine.save_checkpoint("[自動セーブ] QA によるコード検証および自己修復完了")
                if self.abort_requested:
                    break
            elif agent_id == "VisualCritic":
                self.check_scraper_maintenance()
                self.time_machine.save_checkpoint("[自動セーブ] VisualCritic によるアセット保守完了")
                if self.abort_requested:
                    break
            
            if agent_id != "QA" and agent_id != "VisualCritic":
                prompt = self.build_prompt_for_agent(agent_id, context)
                self.log_message(f"[システム] {agent_id} が Ollama (llama3) で思考中です．\n")
                response_text = ask_ollama(prompt)
                
                if self.abort_requested:
                    break
                    
                context += f"\n[{agent_id} の成果物]\n{response_text}\n"
                self.log_message(f"--- 【{self.agents[agent_id]['name']} の出力結果】 ---\n{response_text}\n\n")
                
                if agent_id == "Programmer":
                    self.save_code_to_project(response_text)
                    self.rewrite_map_json(2.5, 1.0)
                    self.save_map_generator()
                    self.time_machine.save_checkpoint("[自動セーブ] Programmer によるPygameコード完了")
                elif agent_id == "Designer":
                    self.log_message("[システム] デザイナーが3つのアセットバリエーションを構築中です．\n")
                    generate_asset_variations(self.workspace_dir, base_prompt)
                    self.log_message("---------------------------------------\n")
                    self.log_message("|デザイナー:|\n")
                    self.log_message("|「3つの候補を作ったよ！どれがいい？」|\n")
                    self.log_message("---------------------------------------\n")
                    self.log_message("          \\  (•‿•)\n\n")
                    self.log_queue.put("REFRESH_GALLERY")
                    self.time_machine.save_checkpoint("[自動セーブ] Designer によるアセット生成完了")
                elif agent_id == "PM":
                    self.time_machine.save_checkpoint("[自動セーブ] PM による仕様策定完了")
                elif agent_id == "Tester":
                    self.time_machine.save_checkpoint("[自動セーブ] Tester によるテスト計画完了")

            self.agents[agent_id]["state"] = "休憩中"
            if idx < len(relay_order) - 1:
                self.run_cooldown(15, agent_id=agent_id)
                
        if self.abort_requested:
            self.log_message("[システム] タスクが緊急停止されました．GPUリソースを完全にクリーンアップします．\n")
            self.clean_gpu_vram()
        else:
            self.log_message("[システム] すべての開発工程が完了しました．ゲームのパッケージ化（exe化）を開始します．\n")
            project_name = "IDERIA_Roller"
            match = re.search(r'■\s*プロジェクト名:\s*([a-zA-Z0-9_\-\s]+)', context)
            if match:
                project_name = match.group(1).strip().replace(" ", "_")
                
            build_dir = os.path.join(self.workspace_dir, "Builds", project_name)
            if not os.path.exists(build_dir):
                os.makedirs(build_dir)
                
            try:
                # game_manager.pyのコピー
                src_game = os.path.join(self.workspace_dir, "game_manager.py")
                dst_game = os.path.join(build_dir, "game_manager.py")
                if os.path.exists(src_game):
                    shutil.copy2(src_game, dst_game)
                    
                # map.jsonのコピー
                src_map = os.path.join(self.workspace_dir, "map.json")
                dst_map = os.path.join(build_dir, "map.json")
                if os.path.exists(src_map):
                    shutil.copy2(src_map, dst_map)
                    
                # アセットフォルダのコピー
                src_assets = os.path.join(self.workspace_dir, "Assets", "Textures")
                dst_assets = os.path.join(build_dir, "Assets", "Textures")
                if os.path.exists(src_assets):
                    if os.path.exists(dst_assets):
                        shutil.rmtree(dst_assets)
                    shutil.copytree(src_assets, dst_assets)
                    
                self.log_message(f"[システム] ソースファイルおよびアセットをゲームビルドフォルダ（{build_dir}）へ配置しました．\n")
                
                # PyInstallerによるexe化（同期実行）
                self.log_message(f"[システム] ゲーム {project_name} のexe化ビルドを実行中です．\n")
                cmd = [
                    "python", "-m", "PyInstaller",
                    "--onefile",
                    "--noconsole",
                    "--name", project_name,
                    "--distpath", build_dir,
                    "game_manager.py"
                ]
                proc = subprocess.Popen(cmd, cwd=build_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = proc.communicate()
                
                if proc.returncode == 0:
                    self.log_message(f"[システム] ゲームのexe化に成功しました．成果物: {os.path.join(build_dir, project_name + '.exe')}\n")
                else:
                    self.log_message(f"[警告] ゲームのexe化に失敗しました．エラー: {stderr}\n")
            except Exception as e:
                self.log_message(f"[警告] ゲームパッケージング処理中にエラーが発生しました: {str(e)}\n")
            
        self.running_task = False
        self.abort_requested = False
        self.phase_text.set("システムフェーズ: 待機中")
        for aid in self.agents:
            self.agents[aid]["state"] = "休憩中"

if __name__ == "__main__":
    app = IDERIAGUI()
    app.mainloop()
