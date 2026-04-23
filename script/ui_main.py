import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from ai_engine import DocEngine
from export_engine import ExportEngine

# 配置信息
FIXED_API_KEY = "sk-f38b529997ef4760bb468d74f54f7b03"
FIXED_APP_ID = "e0cf1cac638f4a2da01973073a1ceb06"

class App:
    def __init__(self, root):
        self.root = root
        root.title("Technical LLD Master v14.0 (Modular Edition)")
        root.geometry("750x650")
        
        self.ai = DocEngine(FIXED_API_KEY, FIXED_APP_ID)
        self.exporter = ExportEngine()

        f = ttk.Frame(root, padding=25); f.pack(fill="both", expand=True)
        ttk.Label(f, text="Source Folder:").pack(anchor="w")
        self.path = ttk.Entry(f); self.path.pack(fill="x", pady=10)
        ttk.Button(f, text="Browse", command=self.browse).pack()
        
        self.btn = tk.Button(f, text="GENERATE DOCUMENTATION", bg="#3dcd58", fg="white", font=("Arial", 11, "bold"), command=self.start, height=2)
        self.btn.pack(fill="x", pady=20)
        
        self.log = scrolledtext.ScrolledText(f, height=18, bg="#1c1c1c", fg="#3dcd58"); self.log.pack(fill="both")
        sys.stdout = self

    def write(self, s):
        self.log.insert(tk.END, s)
        self.log.see(tk.END)
        self.log.update_idletasks()

    def flush(self): pass

    def browse(self):
        p = filedialog.askdirectory()
        if p: self.path.delete(0, tk.END); self.path.insert(0, p)

    def start(self):
        if not self.path.get(): return
        self.btn.config(state="disabled")
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        try:
            folder = self.path.get().strip()
            curr_name = os.path.basename(folder)
            base_title = f"{curr_name}_LLD"
            
            # 1. 扫描代码与旧文档
            local_code = ""
            context_md = "NONE"
            base_md_path = os.path.join(folder, f"{base_title}.md")
            
            if os.path.exists(base_md_path):
                with open(base_md_path, 'r', encoding='utf-8') as f:
                    context_md = f.read()
                print(f">>> 发现历史版本文档...")

            for f in os.listdir(folder):
                if f.endswith(('.c', '.h')):
                    with open(os.path.join(folder, f), 'r', encoding='utf-8', errors='ignore') as f_obj:
                        local_code += f"\n// FILE: {f}\n" + f_obj.read()

            if not local_code:
                print("!!! 未发现 .c 或 .h 文件，跳过。")
                return

            # 2. 调用 AI
            print(f">>> 正在请求 AI 分析: {curr_name}...")
            new_md = self.ai.call_ai(local_code, curr_name, context_md)
            
            # 3. 归档与导出
            self.ai.archive_old_files(folder, base_title, context_md)
            self.exporter.export(new_md, base_title, folder)
            
            print(f"\n🎉 MISSION SUCCESS. Documents saved in: {folder}")
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: {e}")
        finally:
            self.btn.config(state="normal")

if __name__ == "__main__":
    # 禁用代理（可选，视环境而定）
    for key in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
        if key in os.environ: del os.environ[key]
        
    root = tk.Tk()
    App(root)
    root.mainloop()