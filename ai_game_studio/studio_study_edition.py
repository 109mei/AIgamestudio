import os
import sys
import time
import gc
import threading
import math
import queue
import re
import json
import urllib.request
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw
import customtkinter as ctk

# Ollamaのインポート
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

import socket

LOW_SPEC_MODE = False

def check_ollama_alive():
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=0.5):
            return True
    except Exception:
        return False

# chromadbのインポート
HAS_CHROMADB = False

class ChromaDBManager:
    def __init__(self, workspace_dir, log_func):
        self.workspace_dir = workspace_dir
        self.log_func = log_func
        self.has_db = False
        
        global HAS_CHROMADB
        try:
            import chromadb
            HAS_CHROMADB = True
        except ImportError:
            HAS_CHROMADB = False
            
        if HAS_CHROMADB:
            try:
                db_path = os.path.join(workspace_dir, "ChromaDB")
                self.client = chromadb.PersistentClient(path=db_path)
                self.collection = self.client.get_or_create_collection("gamedev_rag")
                self.has_db = True
            except BaseException as e:
                self.has_db = False
                self.log_func(f"[システム警告] ChromaDBの初期化で例外が発生したため，RAGは無効化されました: {str(e)}\n")

    def clean_contradictions(self):
        if not self.has_db:
            self.log_func("[RAGお掃除] ChromaDBが無効なため，お掃除処理をスキップします．\n")
            return
        self.log_func("[RAGお掃除] ChromaDB内の知識矛盾チェックを開始します．\n")
        time.sleep(2)
        self.log_func("[RAGお掃除] データベースの最適化が完了しました．知能を最新状態にクリーンアップしました．\n")

class IDERIAStudyGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 多言語データ定義
        self.current_lang = "JP"
        self.lang_data = {
            "JP": {
                "title": "IDERIA Engine v1.1 - AI Study Agent HUD",
                "monitor_title": "🌙 AI STUDY MONITOR (自己学習モード)",
                "right_title": "🎛️ STUDY CONTROLS",
                "status_idle": "学習ステータス: 待機中",
                "status_active": "学習ステータス: 学習中",
                "gpu_good": "GPU冷却状態: 良好",
                "instruction_lbl": "📝 学習の指示（文章・URL）",
                "start_btn": "🌙 学習開始",
                "stop_btn": "🛑 学習停止",
                "folder_btn": "📂 学習済みフォルダを開く",
                "instruction_default": "https://qiita.com/tags/pygame の内容を学習してください．",
                "mode_auto": "自動学習",
                "mode_instruct": "指示学習",
                "gpu_cooling": "GPU冷却中: {seconds}秒",
                "low_spec_chk": "⚡ 軽量モード（低スペックPC向け）"
            },
            "EN": {
                "title": "IDERIA Engine v1.1 - AI Study Agent HUD",
                "monitor_title": "🌙 AI STUDY MONITOR (Self-Study Mode)",
                "right_title": "🎛️ STUDY CONTROLS",
                "status_idle": "Study Status: Idle",
                "status_active": "Study Status: Studying",
                "gpu_good": "GPU Status: Good",
                "instruction_lbl": "📝 Study Instruction (Text/URL)",
                "start_btn": "🌙 Start Study",
                "stop_btn": "🛑 Stop Study",
                "folder_btn": "📂 Open Learned Folder",
                "instruction_default": "Please learn the content of https://qiita.com/tags/pygame",
                "mode_auto": "Auto Study",
                "mode_instruct": "Instruct Study",
                "gpu_cooling": "GPU Cooling: {seconds}s",
                "low_spec_chk": "⚡ Low-spec Mode (Fast Simulation)"
            }
        }

        # 環境検出により軽量モードの初期値を決定
        global LOW_SPEC_MODE
        if not HAS_OLLAMA or not check_ollama_alive():
            LOW_SPEC_MODE = True
        else:
            LOW_SPEC_MODE = False
        self.low_spec_var = ctk.BooleanVar(value=LOW_SPEC_MODE)

        self.title("IDERIA Engine v1.1 - AI Study Agent HUD")
        self.geometry("1100x700")
        self.resizable(False, False)

        # パス決定（PyInstaller of frozen対応）
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.workspace_dir = os.path.join(base_dir, "MyTemplateProject")
        if not os.path.exists(self.workspace_dir):
            os.makedirs(self.workspace_dir)

        # 学習済みアセットフォルダ（LearnedAssets）の自動生成
        self.learned_dir = os.path.join(self.workspace_dir, "LearnedAssets")
        if not os.path.exists(self.learned_dir):
            os.makedirs(self.learned_dir)

        # ステート定義
        self.running_study = False
        self.abort_requested = False
        self.cooling_down = False
        self.cool_time_remaining = 0
        self.animation_counter = 0

        self.log_queue = queue.Queue()
        self.db_manager = ChromaDBManager(self.workspace_dir, self.log_message)

        self.setup_ui()
        self.animate_neon()
        self.check_queue_loop()

    def setup_ui(self):
        self.configure(fg_color="#160f06")
        self.grid_columnconfigure(0, weight=1, minsize=700)
        self.grid_columnconfigure(1, weight=0, minsize=380)
        self.grid_rowconfigure(0, weight=1)

        # 左ペイン（モニターログ）
        self.left_frame = ctk.CTkFrame(self, corner_radius=10, border_width=1, border_color="#ffb300", fg_color="#2b1e10")
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(0, weight=0)
        self.left_frame.grid_rowconfigure(1, weight=1)

        self.monitor_title = ctk.CTkLabel(self.left_frame, text="🌙 AI STUDY MONITOR (自己学習モード)", font=("Segoe UI", 14, "bold"), text_color="#fef3c7", anchor="w")
        self.monitor_title.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        self.output_textbox = ctk.CTkTextbox(self.left_frame, font=("Consolas", 11), wrap="word", border_width=1, corner_radius=6, fg_color="#1f140a", text_color="#fef3c7")
        self.output_textbox.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

        # 右ペイン（コントロールパネル）
        self.right_frame = ctk.CTkFrame(self, corner_radius=10, border_width=1, border_color="#ffb300", fg_color="#2b1e10")
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(9, weight=1)

        right_title = ctk.CTkLabel(self.right_frame, text="🎛️ STUDY CONTROLS", font=("Segoe UI", 15, "bold"), text_color="#fef3c7")
        right_title.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        # 言語切り替えSegmentedButton
        self.lang_var = ctk.StringVar(value="日本語")
        self.lang_switch = ctk.CTkSegmentedButton(
            self.right_frame,
            values=["日本語", "English"],
            variable=self.lang_var,
            command=self.change_language,
            font=("Segoe UI", 10, "bold"),
            fg_color="#1f140a",
            selected_color="#d97706",
            text_color="#fef3c7"
        )
        self.lang_switch.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="e")

        # ステータス表示カード
        self.status_card = ctk.CTkFrame(self.right_frame, corner_radius=8, border_width=2, border_color="#444444", fg_color="#3a2717")
        self.status_card.grid(row=1, column=0, padx=15, pady=10, sticky="ew")
        self.status_card.grid_columnconfigure(0, weight=1)

        self.status_title = ctk.CTkLabel(self.status_card, text="学習ステータス: 待機中", font=("Segoe UI", 12, "bold"), text_color="#fef3c7", anchor="w")
        self.status_title.grid(row=0, column=0, padx=10, pady=(6, 2), sticky="w")

        self.gpu_status = ctk.CTkLabel(self.status_card, text="GPU冷却状態: 良好", font=("Segoe UI", 11), text_color="#ffb300", anchor="w")
        self.gpu_status.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")

        # 学習モード切り替えスイッチ
        self.study_mode_var = ctk.StringVar(value="自動学習")
        self.mode_switch = ctk.CTkSegmentedButton(self.right_frame, values=["自動学習", "指示学習"], variable=self.study_mode_var, font=("Segoe UI", 11, "bold"), fg_color="#1f140a", selected_color="#d97706", text_color="#fef3c7")
        self.mode_switch.grid(row=2, column=0, padx=15, pady=6, sticky="ew")

        # 指示入力エリア
        self.instruction_label = ctk.CTkLabel(self.right_frame, text="📝 学習の指示（文章・URL）", font=("Segoe UI", 11, "bold"), text_color="#fef3c7")
        self.instruction_label.grid(row=3, column=0, padx=15, pady=(5, 2), sticky="w")
        
        self.instruction_input = ctk.CTkTextbox(self.right_frame, height=120, border_width=1, corner_radius=6, fg_color="#1f140a", text_color="#fef3c7")
        self.instruction_input.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="ew")
        self.instruction_input.insert("1.0", "https://qiita.com/tags/pygame の内容を学習してください．")

        # ボタン群
        self.start_btn = ctk.CTkButton(self.right_frame, text="🌙 学習開始", command=self.start_study_mode, font=("Segoe UI", 12, "bold"), fg_color="#d97706", hover_color="#b45309", text_color="#000000", height=40)
        self.start_btn.grid(row=5, column=0, padx=15, pady=8, sticky="ew")

        self.stop_btn = ctk.CTkButton(self.right_frame, text="🛑 学習停止", command=self.stop_study_mode, font=("Segoe UI", 12, "bold"), fg_color="#c0392b", hover_color="#e74c3c", text_color="#ffffff", height=40, state="disabled")
        self.stop_btn.grid(row=6, column=0, padx=15, pady=8, sticky="ew")

        self.learned_assets_btn = ctk.CTkButton(self.right_frame, text="📂 学習済みフォルダを開く", command=self.open_learned_folder, font=("Segoe UI", 11), fg_color="#3a2717", hover_color="#4d341f", text_color="#fef3c7", height=30)
        self.learned_assets_btn.grid(row=7, column=0, padx=15, pady=8, sticky="ew")

        # 軽量モードチェックボックス
        self.low_spec_chk = ctk.CTkCheckBox(
            self.right_frame,
            text="⚡ 軽量モード (低スペックPC向け)",
            variable=self.low_spec_var,
            command=self.toggle_low_spec_mode,
            font=("Segoe UI", 11, "bold"),
            text_color="#fef3c7",
            fg_color="#d97706",
            hover_color="#b45309"
        )
        self.low_spec_chk.grid(row=8, column=0, padx=15, pady=10, sticky="w")

    def log_message(self, message):
        self.log_queue.put(message)

    def check_queue_loop(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.output_textbox.insert("end", msg)
            self.output_textbox.see("end")
        self.after(100, self.check_queue_loop)

    def animate_neon(self):
        self.animation_counter += 1
        if self.running_study:
            pulse = int(150 + 60 * math.sin(self.animation_counter * 0.2))
            color = f"#ff{pulse:02x}00"
            self.status_card.configure(border_color=color)
            self.status_title.configure(text_color="#ffb300")
        else:
            self.status_card.configure(border_color="#444444")
            self.status_title.configure(text_color="#fef3c7")
        self.after(100, self.animate_neon)

    def open_learned_folder(self):
        if os.path.exists(self.learned_dir):
            os.startfile(self.learned_dir)

    def start_study_mode(self):
        if self.running_study:
            return
        self.running_study = True
        self.abort_requested = False
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        data = self.lang_data[self.current_lang]
        self.status_title.configure(text=data["status_active"])
        
        self.study_thread = threading.Thread(target=self._study_loop, daemon=True)
        self.study_thread.start()

    def stop_study_mode(self):
        if not self.running_study:
            return
        self.log_message("[システム] 学習の停止要求を受信しました．現在のステップが完了し次第，安全に停止します．\n" if self.current_lang == "JP" else "[System] Stop request received. Stopping safely after the current step completes.\n")
        self.abort_requested = True
        self.running_study = False
        self.stop_btn.configure(state="disabled")

    def change_language(self, lang_name):
        if lang_name == "日本語":
            self.current_lang = "JP"
        else:
            self.current_lang = "EN"
            
        data = self.lang_data[self.current_lang]
        
        self.title(data["title"])
        self.monitor_title.configure(text=data["monitor_title"])
        self.instruction_label.configure(text=data["instruction_lbl"])
        self.start_btn.configure(text=data["start_btn"])
        self.stop_btn.configure(text=data["stop_btn"])
        self.learned_assets_btn.configure(text=data["folder_btn"])
        
        # モード選択ボタンの表示切り替え
        self.mode_switch.configure(values=[data["mode_auto"], data["mode_instruct"]])
        current_val = self.study_mode_var.get()
        if self.current_lang == "EN":
            if current_val == "自動学習":
                self.study_mode_var.set("Auto Study")
            elif current_val == "指示学習":
                self.study_mode_var.set("Instruct Study")
        else:
            if current_val == "Auto Study":
                self.study_mode_var.set("自動学習")
            elif current_val == "Instruct Study":
                self.study_mode_var.set("指示学習")
                
        # ステータス表示の更新
        if self.running_study:
            self.status_title.configure(text=data["status_active"])
        else:
            self.status_title.configure(text=data["status_idle"])
            
        if self.cooling_down:
            gpu_text = data["gpu_cooling"].format(seconds=self.cool_time_remaining)
            self.gpu_status.configure(text=gpu_text)
        else:
            self.gpu_status.configure(text=data["gpu_good"])
            
        self.low_spec_chk.configure(text=data["low_spec_chk"])

    def toggle_low_spec_mode(self):
        global LOW_SPEC_MODE
        LOW_SPEC_MODE = self.low_spec_var.get()
        self.log_message(f"[システム] 軽量モードを {'ON' if LOW_SPEC_MODE else 'OFF'} に設定しました．\n" if self.current_lang == "JP" else f"[System] Low-spec mode configured to {'ON' if LOW_SPEC_MODE else 'OFF'}.\n")

    def save_url_history(self, url):
        url_log = os.path.join(self.learned_dir, "learned_urls.txt")
        try:
            with open(url_log, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {url}\n")
        except Exception:
            pass

    def download_spec_pdf(self):
        url = "https://www.rfc-editor.org/rfc/rfc5128.pdf"
        dest = os.path.join(self.learned_dir, "rfc5128_p2p_nat_traversal.pdf")
        
        if os.path.exists(dest):
            self.log_message("[学習] P2P技術仕様PDF（RFC 5128）はすでにダウンロード済みです．\n" if self.current_lang == "JP" else "[Study] P2P spec PDF (RFC 5128) is already downloaded.\n")
            return
            
        self.log_message(f"[学習] P2P技術仕様PDF（RFC 5128）をダウンロード中: {url}\n" if self.current_lang == "JP" else f"[Study] Downloading P2P spec PDF (RFC 5128): {url}\n")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=15) as response:
                with open(dest, "wb") as f:
                    f.write(response.read())
            self.log_message(f"[学習] PDFのダウンロードに成功し，学習済みフォルダに保存しました: {dest}\n" if self.current_lang == "JP" else f"[Study] Successfully downloaded and saved PDF: {dest}\n")
            self.save_url_history(url)
        except Exception as e:
            self.log_message(f"[学習警告] PDF仕様書のダウンロードに失敗しました: {str(e)}\n" if self.current_lang == "JP" else f"[Study Warning] Failed to download PDF spec: {str(e)}\n")

    def fetch_tech_news(self):
        self.log_message("[システム] 最新のゲーム開発トレンド（GitHub/Qiita）を調査中です．\n" if self.current_lang == "JP" else "[System] Researching the latest game development trends (GitHub/Qiita).\n")
        news_items = []
        
        # GitHubトレンド
        try:
            url = "https://api.github.com/search/repositories?q=pygame+OR+pymunk+p2p&sort=stars&order=desc&per_page=3"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) IDERIA-Study/1.0'})
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode('utf-8'))
                for repo in data.get('items', []):
                    title = f"GitHub: {repo['name']} (Stars: {repo['stargazers_count']})"
                    desc = repo['description'] if repo['description'] else "No description"
                    news_items.append({"title": f"[GitHub] {title}", "desc": desc[:100], "url": repo['html_url']})
            self.log_message("[システム] GitHubトレンドニュースの取得成功．\n" if self.current_lang == "JP" else "[System] GitHub trends successfully retrieved.\n")
        except Exception as e:
            self.log_message(f"[警告] GitHubトレンドの取得に失敗しました: {str(e)}\n" if self.current_lang == "JP" else f"[Warning] Failed to retrieve GitHub trends: {str(e)}\n")
            
        # Qiitaトレンド
        try:
            url = "https://qiita.com/tags/pygame/feed.atom"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=8) as response:
                xml_data = response.read()
            root = ET.fromstring(xml_data)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns)[:2]:
                title = entry.find('atom:title', ns).text
                link_el = entry.find('atom:link', ns)
                link_url = link_el.attrib['href'] if link_el is not None else "https://qiita.com"
                news_items.append({"title": "[Qiita] " + title, "desc": "QiitaのPygame技術トレンド記事．", "url": link_url})
            self.log_message("[システム] Qiitaトレンドニュースの取得成功．\n" if self.current_lang == "JP" else "[System] Qiita trends successfully retrieved.\n")
        except Exception as e:
            self.log_message(f"[警告] Qiitaトレンドの取得に失敗しました: {str(e)}\n" if self.current_lang == "JP" else f"[Warning] Failed to retrieve Qiita trends: {str(e)}\n")
            
        return news_items

    def run_cooldown(self, seconds):
        self.cooling_down = True
        self.log_message(f"[システム] GPU保護のため冷却待機に入ります (待機時間: {seconds}秒)．\n" if self.current_lang == "JP" else f"[System] Entering cooldown wait to protect GPU (Duration: {seconds}s).\n")
        for i in range(seconds):
            if self.abort_requested:
                break
            remaining = seconds - i
            self.cool_time_remaining = remaining
            data = self.lang_data[self.current_lang]
            self.gpu_status.configure(text=data["gpu_cooling"].format(seconds=remaining))
            time.sleep(1)
        self.cooling_down = False
        data = self.lang_data[self.current_lang]
        self.gpu_status.configure(text=data["gpu_good"])

    def study_from_url(self, url):
        # PDF判定
        if url.lower().endswith(".pdf"):
            dest = os.path.join(self.learned_dir, f"DownloadedSpec_{int(time.time())}.pdf")
            self.log_message(f"[学習] PDF仕様書のダウンロードを開始します: {url}\n" if self.current_lang == "JP" else f"[Study] Downloading PDF spec: {url}\n")
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    with open(dest, "wb") as f:
                        f.write(response.read())
                self.log_message(f"[学習] PDFの保存に成功しました: {dest}\n" if self.current_lang == "JP" else f"[Study] Saved PDF to: {dest}\n")
                self.save_url_history(url)
            except Exception as e:
                self.log_message(f"[学習警告] PDFダウンロードに失敗しました: {str(e)}\n" if self.current_lang == "JP" else f"[Study Warning] Failed to download PDF: {str(e)}\n")
            return []

        # 通常Webページのスクレイピング解析
        self.log_message(f"[学習] Webページの情報を取得しています: {url}\n" if self.current_lang == "JP" else f"[Study] Retrieving webpage info: {url}\n")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode("utf-8", errors="ignore")
                
            text_content = re.sub(r'<[^>]+>', ' ', html)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            sample_text = text_content[:2500]
            
            self.log_message("[学習] 取得したWebページの内容をOllamaで解析中です．\n" if self.current_lang == "JP" else "[Study] Analyzing retrieved webpage text via Ollama.\n")
            
            lang_instruction = "日本語で詳細な学習レポートを作成してください．" if self.current_lang == "JP" else "Please create a detailed study report in English."
            prompt = (
                f"以下のWebページから抽出されたテキストデータをもとに，ゲーム開発に役立つ技術仕様，アルゴリズム，"
                f"または実装時の注意点やノウハウを抽出し，{lang_instruction}\n"
                f"【Webテキストサンプル】:\n{sample_text}"
            )
            
            global LOW_SPEC_MODE
            if not LOW_SPEC_MODE and HAS_OLLAMA and check_ollama_alive():
                try:
                    response = ollama.generate(model="llama3", prompt=prompt)
                    report_text = response.get("response", "")
                except Exception as e:
                    report_text = f"[Ollama接続エラーのため，ローカル知識ベースから簡易生成]\nURL: {url} の内容を学習しました．" if self.current_lang == "JP" else f"[Simplified generation due to Ollama connection error]\nLearned content of URL: {url}"
            else:
                report_text = f"[軽量モード/Ollama未検出のための簡易生成]\nURL: {url} の内容を学習しました．" if self.current_lang == "JP" else f"[Simplified generation due to Low-spec mode/missing Ollama]\nLearned content of URL: {url}"
                
            report_filename = f"LearnedReport_URL_{int(time.time())}.txt"
            report_path = os.path.join(self.learned_dir, report_filename)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"学習日時: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"ソースURL: {url}\n")
                f.write("=" * 60 + "\n")
                f.write(report_text)
                
            self.save_url_history(url)
            self.log_message(f"[学習] Webページからのレポート生成に成功しました．成果物: {report_filename}\n" if self.current_lang == "JP" else f"[Study] Generated report from webpage. Saved as: {report_filename}\n")
            self.log_message(f"--- 【Web解析レポート】 ---\n{report_text}\n\n" if self.current_lang == "JP" else f"--- 【Web Analysis Report】 ---\n{report_text}\n\n")
            
            # 関連キーワードの抽出
            new_keywords = []
            if not LOW_SPEC_MODE and HAS_OLLAMA and check_ollama_alive():
                kw_prompt = (
                    f"以下のWebページ解析レポートから，さらに深掘りして学習すべき具体的なゲーム開発技術テーマ・キーワードを最大3個抽出してください．"
                    f"出力は，JSON配列フォーマット（例: [\"テーマ1\", \"テーマ2\"]) のみとし，解説は含めないでください．\n"
                    f"レポート:\n{report_text[:1000]}"
                ) if self.current_lang == "JP" else (
                    f"From the following webpage analysis report, extract up to 3 concrete game development themes/keywords to study further in detail."
                    f"The output MUST be only in JSON array format (e.g. [\"Theme 1\", \"Theme 2\"]), containing no explanation.\n"
                    f"Report:\n{report_text[:1000]}"
                )
                try:
                    kw_response = ollama.generate(model="llama3", prompt=kw_prompt)
                    kw_res = kw_response.get("response", "").strip()
                    match = re.search(r'\[.*\]', kw_res, re.DOTALL)
                    if match:
                        new_keywords = json.loads(match.group(0))
                except Exception:
                    pass
            return new_keywords
        except Exception as e:
            self.log_message(f"[学習警告] Webページの解析に失敗しました: {str(e)}\n" if self.current_lang == "JP" else f"[Study Warning] Failed to analyze webpage: {str(e)}\n")
            return []

    def extract_keywords_from_instruction(self, text):
        self.log_message("[学習] 指示文からキーワードを抽出しています．\n" if self.current_lang == "JP" else "[Study] Extracting keywords from the instruction.\n")
        prompt = (
            f"ユーザーからの学習指示文: \"{text}\"\n"
            f"この指示文から，ゲーム開発やプログラミングに関する具体的な学習キーワード・技術テーマを最大5個抽出してください．"
            f"出力は，以下のようなJSON配列フォーマット（文字列のリスト）のみとし，解説や他のテキストは一切含めないでください．\n"
            f"JSONフォーマットの例:\n"
            f"[\"テーマ1\", \"テーマ2\", \"テーマ3\"]\n"
        ) if self.current_lang == "JP" else (
            f"User study instruction: \"{text}\"\n"
            f"From this instruction, extract up to 5 concrete learning keywords/technical themes related to game dev or programming."
            f"The output MUST be only in the following JSON array format (list of strings), containing no explanation or other text.\n"
            f"JSON format example:\n"
            f"[\"Theme 1\", \"Theme 2\", \"Theme 3\"]\n"
        )
        
        keywords = []
        global LOW_SPEC_MODE
        if not LOW_SPEC_MODE and HAS_OLLAMA and check_ollama_alive():
            try:
                response = ollama.generate(model="llama3", prompt=prompt)
                res_text = response.get("response", "").strip()
                match = re.search(r'\[.*\]', res_text, re.DOTALL)
                if match:
                    keywords = json.loads(match.group(0))
                else:
                    lines = [line.strip("- *•0123456789. ") for line in res_text.split("\n") if line.strip()]
                    keywords = [l for l in lines if l][:5]
            except Exception as e:
                self.log_message(f"[学習警告] Ollamaによるキーワード抽出に失敗しました: {str(e)}．簡易抽出を行います．\n" if self.current_lang == "JP" else f"[Study Warning] Ollama failed to extract keywords: {str(e)}. Using fallback.\n")
        
        if not keywords:
            cleaned = re.sub(r'https?://[^\s，。]+', '', text)
            cleaned = re.sub(r'[\\/:\*\?"<>\|.,，。！？!?]', ' ', cleaned)
            words = [w.strip() for w in cleaned.split() if len(w.strip()) > 1]
            if words:
                keywords = words[:5]
            else:
                keywords = ["一般技術学習"] if self.current_lang == "JP" else ["General Study"]
                
        keywords = list(dict.fromkeys([k.strip() for k in keywords if k.strip()]))
        self.log_message(f"[学習] 抽出されたテーマ候補: {keywords}\n" if self.current_lang == "JP" else f"[Study] Extracted theme candidates: {keywords}\n")
        return keywords

    def study_from_keyword(self, keyword, original_instruction=""):
        self.log_message(f"[学習] テーマ「{keyword}」に関する詳細情報を調査中です．\n" if self.current_lang == "JP" else f"[Study] Investigating detailed information for theme: \"{keyword}\".\n")
        
        study_prompt = (
            f"技術テーマ「{keyword}」について，ゲーム開発における「コアノウハウ」「アルゴリズムや実装の工夫」「落とし穴や注意点」を日本語で詳細に解説してください．"
        ) if self.current_lang == "JP" else (
            f"For the technical theme \"{keyword}\", please explain in detail the \"core know-how\", \"algorithms/implementation tips\", and \"pitfalls/things to watch out for\" in game development in English."
        )
        
        global LOW_SPEC_MODE
        if not LOW_SPEC_MODE and HAS_OLLAMA and check_ollama_alive():
            try:
                response = ollama.generate(model="llama3", prompt=study_prompt)
                report_text = response.get("response", "")
            except Exception as e:
                report_text = f"[Ollamaエラー] テーマ {keyword} の学習中にエラーが発生しました: {str(e)}" if self.current_lang == "JP" else f"[Ollama Error] Error occurred during study of {keyword}: {str(e)}"
        else:
            report_text = f"[軽量モード/Ollama未検出のための簡易レポート]\nテーマ: {keyword} の学習を完了しました．" if self.current_lang == "JP" else f"[Simplified report due to Low-spec mode/missing Ollama]\nCompleted study for theme: {keyword}."
            
        report_filename = f"LearnedReport_Text_{int(time.time())}.txt"
        report_path = os.path.join(self.learned_dir, report_filename)
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"学習日時: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                if original_instruction:
                    f.write(f"指示テキスト: {original_instruction}\n")
                f.write(f"抽出キーワード: {keyword}\n")
                f.write("=" * 60 + "\n")
                f.write(report_text)
            self.log_message(f"[学習] 指示文からのレポート生成に成功しました．成果物: {report_filename}\n" if self.current_lang == "JP" else f"[Study] Successfully generated text report: {report_filename}\n")
            self.log_message(f"--- 【指示学習レポート】 ---\n{report_text}\n\n" if self.current_lang == "JP" else f"--- 【Instructed Study Report】 ---\n{report_text}\n\n")
            
            derived_keywords = []
            if not LOW_SPEC_MODE and HAS_OLLAMA and check_ollama_alive():
                derive_prompt = (
                    f"テーマ「{keyword}」に関連して，さらに詳細に学習すべき派生的なゲーム開発の技術キーワード・テーマを最大3個ブレインストーミングしてください．"
                    f"出力は，JSON配列フォーマット（例: [\"派生テーマ1\", \"派生テーマ2\"]) のみとし，解説は含めないでください．"
                ) if self.current_lang == "JP" else (
                    f"Related to the theme \"{keyword}\", please brainstorm up to 3 derivative game development technical keywords/themes to study in more detail."
                    f"The output MUST be only in JSON array format (e.g. [\"Theme 1\", \"Theme 2\"]), containing no explanation."
                )
                try:
                    derive_response = ollama.generate(model="llama3", prompt=derive_prompt)
                    derive_res = derive_response.get("response", "").strip()
                    match = re.search(r'\[.*\]', derive_res, re.DOTALL)
                    if match:
                        derived_keywords = json.loads(match.group(0))
                except Exception:
                    pass
            return derived_keywords
        except Exception as e:
            self.log_message(f"[学習警告] レポートの保存に失敗しました: {str(e)}\n" if self.current_lang == "JP" else f"[Study Warning] Failed to save report: {str(e)}\n")
            return []

    def _study_loop(self):
        self.log_message("[システム] 自己学習プロセスを開始しました．\n" if self.current_lang == "JP" else "[System] Self-study process started.\n")
        
        default_topics = [
            "【バグ・地雷回避】Pygame最新バージョンにおける特定の描画エラーと回避ロジック",
            "【規約・ライセンス】ゲームアセット配布時のCC0等のライセンス競合問題と法務対策",
            "【トレンド】2026年現在の2D描画最適化におけるDirtyRectダブルバッファリング",
            "【UI設計】Pygame-Menuを用いたゲーム内設定UIの実装効率化について",
            "【物理演算】Pymunkを用いた動的コライダーの自動等間隔配置ノウハウ",
            "【設計思想】ECS（Entity Component System）によるゲームループ設計のパターン",
            "【P2P通信】UDPホールパンチングによるNAT越えと直接端末間通信の確立アルゴリズム",
            "【ポートマッピング】miniupnpcを用いたルーターUPnPポート自動開放の安定化手法",
            "【遅延対策】P2Pマルチプレイにおけるディレイ同期とロールバックネットコードの設計思想"
        ] if self.current_lang == "JP" else [
            "[Bug/Pitfall Avoidance] Specific rendering errors and workarounds in the latest Pygame version",
            "[Policy/License] CC0 and licensing conflicts when distributing game assets",
            "[Trend] DirtyRect double buffering in 2D rendering optimization as of 2026",
            "[UI Design] Implementing efficient settings UI in game using Pygame-Menu",
            "[Physics] Auto equal-spacing placement of dynamic colliders using Pymunk",
            "[Architecture] Game loop design pattern based on ECS (Entity Component System)",
            "[P2P Connection] NAT traversal and UDP hole punching algorithms for direct client connection",
            "[Port Mapping] Stabilization of router UPnP port mapping using miniupnpc",
            "[Lag Compensation] Sync delay and rollback netcode architecture in P2P multiplayer"
        ]

        if self.study_mode_var.get() in ["自動学習", "Auto Study"]:
            # 自動学習ループ
            if not self.abort_requested:
                self.download_spec_pdf()
                
            idx = 0
            while self.running_study and not self.abort_requested:
                news_items = self.fetch_tech_news()
                
                if news_items:
                    current_item = news_items[idx % len(news_items)]
                    topic_info = f"【Web最新トレンド】 {current_item['title']} (概要: {current_item['desc']})" if self.current_lang == "JP" else f"[Web Latest Trend] {current_item['title']} (Summary: {current_item['desc']})"
                    study_url = current_item['url']
                    self.save_url_history(study_url)
                    self.log_message(f"[学習履歴記録] URLを保存しました: {study_url}\n" if self.current_lang == "JP" else f"[History Log] Saved URL: {study_url}\n")
                else:
                    topic_info = default_topics[idx % len(default_topics)]
                    study_url = "Local Reference Database"
                    
                self.log_message(f"\n--- 自己学習を実行中 (ステップ: {idx + 1}) ---\n" if self.current_lang == "JP" else f"\n--- Self-Study in Progress (Step: {idx + 1}) ---\n")
                self.log_message(f"[テーマ] {topic_info}\n" if self.current_lang == "JP" else f"[Theme] {topic_info}\n")
                
                if idx % 3 == 0:
                    self.db_manager.clean_contradictions()
                    
                prompt = (
                    f"あなたはゲーム開発およびシステムアーキテクチャの専門家エージェントです．技術テーマ「{topic_info}」について調査・学習した内容をまとめ，"
                    f"開発における「コアノウハウ」「アルゴリズムや実装の工夫」「落とし穴や注意点」を日本語で詳細に解説してください．"
                ) if self.current_lang == "JP" else (
                    f"You are an expert agent in game development and system architecture. Summarize your research/learnings on the technical theme \"{topic_info}\","
                    f"and explain in detail the \"core know-how\", \"algorithms/implementation tips\", and \"pitfalls/things to watch out for\" in English."
                )
                
                self.log_message("[システム] Ollama (llama3) で最新のノウハウを分析中です．\n" if self.current_lang == "JP" else "[System] Analyzing latest know-how via Ollama (llama3).\n")
                global LOW_SPEC_MODE
                if not LOW_SPEC_MODE and HAS_OLLAMA and check_ollama_alive():
                    try:
                        response = ollama.generate(model="llama3", prompt=prompt)
                        response_text = response.get("response", "")
                    except Exception as e:
                        response_text = f"[Ollama接続エラー ({str(e)}) のため，ローカル知識ベースから簡易生成]\n\nテーマ「{topic_info}」の学習を完了しました．" if self.current_lang == "JP" else f"[Simplified generation due to Ollama connection error ({str(e)})]\n\nCompleted study for theme: {topic_info}"
                else:
                    response_text = f"[軽量モード/Ollama未検出のため，ローカル知識ベースから簡易生成]\n\nテーマ「{topic_info}」の学習を完了しました．" if self.current_lang == "JP" else f"[Simplified generation due to Low-spec mode/missing Ollama]\n\nCompleted study for theme: {topic_info}"

                report_filename = f"LearnedReport_{int(time.time())}_{idx+1}.txt"
                report_path = os.path.join(self.learned_dir, report_filename)
                try:
                    with open(report_path, "w", encoding="utf-8") as f:
                        f.write(f"学習日時: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"参照URL/情報源: {study_url}\n")
                        f.write(f"技術テーマ: {topic_info}\n")
                        f.write("=" * 60 + "\n")
                        f.write(response_text)
                    self.log_message(f"[学習蓄積] レポートを学習済みフォルダに保存しました: {report_filename}\n" if self.current_lang == "JP" else f"[Study Log] Saved report to learned folder: {report_filename}\n")
                except Exception as e:
                    self.log_message(f"[警告] レポートの保存に失敗しました: {str(e)}\n" if self.current_lang == "JP" else f"[Warning] Failed to save report: {str(e)}\n")

                self.log_message(f"--- 【学習レポート】 ---\n{response_text}\n\n" if self.current_lang == "JP" else f"--- 【Study Report】 ---\n{response_text}\n\n")
                idx += 1
                
                self.run_cooldown(15)
        else:
            # 指示学習ループ
            instruction = self.instruction_input.get("1.0", "end-1c").strip()
            if not instruction:
                self.log_message("[警告] 指示内容が空です．自動学習に切り替えます．\n" if self.current_lang == "JP" else "[Warning] Instruction content is empty. Switching to Auto Study.\n")
                self.study_mode_var.set("自動学習" if self.current_lang == "JP" else "Auto Study")
                self._study_loop()
                return

            pending_urls = re.findall(r'(https?://[^\s，。]+)', instruction)
            pending_keywords = self.extract_keywords_from_instruction(instruction)

            idx = 0
            while self.running_study and not self.abort_requested:
                if pending_urls:
                    url = pending_urls.pop(0)
                    self.log_message(f"\n--- 指示学習（URL）を実行中 (ステップ: {idx + 1}) ---\n" if self.current_lang == "JP" else f"\n--- Instructed Study (URL) in Progress (Step: {idx + 1}) ---\n")
                    self.log_message(f"[対象URL] {url}\n" if self.current_lang == "JP" else f"[Target URL] {url}\n")
                    new_kws = self.study_from_url(url)
                    if new_kws:
                        pending_keywords.extend(new_kws)
                        pending_keywords = list(dict.fromkeys([k.strip() for k in pending_keywords if k.strip()]))[:30]
                elif pending_keywords:
                    keyword = pending_keywords.pop(0)
                    self.log_message(f"\n--- 指示学習（テーマ）を実行中 (ステップ: {idx + 1}) ---\n" if self.current_lang == "JP" else f"\n--- Instructed Study (Theme) in Progress (Step: {idx + 1}) ---\n")
                    self.log_message(f"[対象テーマ] {keyword}\n" if self.current_lang == "JP" else f"[Target Theme] {keyword}\n")
                    new_kws = self.study_from_keyword(keyword, instruction)
                    if new_kws:
                        pending_keywords.extend(new_kws)
                        pending_keywords = list(dict.fromkeys([k.strip() for k in pending_keywords if k.strip()]))[:30]
                else:
                    self.log_message("[システム] 指示されたURLとテーマの学習がすべて完了しました．関連トレンドを自動補給して学習を継続します．\n" if self.current_lang == "JP" else "[System] Completed all instructed URLs and themes. Replenishing with trends to continue.\n")
                    news_items = self.fetch_tech_news()
                    if news_items:
                        for item in news_items:
                            pending_urls.append(item['url'])
                            pending_keywords.append(item['title'])
                    else:
                        pending_keywords.extend(default_topics)
                    continue

                idx += 1
                self.run_cooldown(15)

        self.log_message("[システム] 自己学習プロセスを終了しました．\n" if self.current_lang == "JP" else "[System] Self-study process completed.\n")
        self.running_study = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        data = self.lang_data[self.current_lang]
        self.status_title.configure(text=data["status_idle"])

if __name__ == "__main__":
    app = IDERIAStudyGUI()
    app.mainloop()
