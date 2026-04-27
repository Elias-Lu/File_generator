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

# 忽略的文件夹黑名单
IGNORE_DIRS = {
    "build", "Debug", "Release", "bin", "obj", 
    ".git", ".svn", ".vscode", ".idea", 
    "archive", "Output"
}

class App:
    def __init__(self, root):
        self.root = root
        root.title("Technical LLD Master v16.0 (Recursive Architecture)")
        root.geometry("800x700")
        
        self.ai = DocEngine(FIXED_API_KEY, FIXED_APP_ID)
        self.exporter = ExportEngine()

        f = ttk.Frame(root, padding=25); f.pack(fill="both", expand=True)
        ttk.Label(f, text="Select Root Project Folder:").pack(anchor="w")
        
        self.path = ttk.Entry(f); self.path.pack(fill="x", pady=10)
        ttk.Button(f, text="Browse", command=self.browse).pack()
        
        self.btn = tk.Button(f, text="START MULTI-LEVEL GENERATION", 
                             bg="#3dcd58", fg="white", font=("Arial", 11, "bold"), 
                             command=self.start)
        self.btn.pack(fill="x", pady=20)
        
        self.log = scrolledtext.ScrolledText(f, height=20, font=("Consolas", 10))
        self.log.pack(fill="both", expand=True)
        
        sys.stdout = self

    def write(self, txt):
        if txt is not None:
            self.log.insert(tk.END, str(txt))
            self.log.see(tk.END)

    def flush(self):
        pass

    def browse(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path.delete(0, tk.END)
            self.path.insert(0, directory)

    def start(self):
        folder = self.path.get().strip()
        if not folder or not os.path.exists(folder):
            print("!!! 请选择有效的项目根目录。")
            return
        
        self.btn.config(state="disabled")
        self.log.delete(1.0, tk.END)
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        try:
            root_path = self.path.get().strip()
            print(f"🚀 --- 启动深度优先递归扫描 ---")
            print(f"项目根路径: {root_path}\n")
            
            # 执行核心递归分析
            self.analyze_recursive(root_path)
            
            print(f"\n🎉 [任务完成] 所有层级的技术手册已生成并归档。")
            
        except Exception as e:
            print(f"\n❌ [严重错误]: {str(e)}")
        finally:
            self.btn.config(state="normal")

    def analyze_recursive(self, current_path):
        """
        核心递归函数：逐级向下钻取，并向上汇总
        """
        current_name = os.path.basename(current_path)
        sub_summaries = []  # 存储下级模块传回的摘要
        
        # 1. 深度优先：先递归处理所有子目录
        try:
            items = os.listdir(current_path)
        except Exception as e:
            print(f"!!! 无法访问目录 {current_name}: {e}")
            return None

        for item in items:
            full_path = os.path.join(current_path, item)
            if os.path.isdir(full_path):
                # 过滤逻辑
                if item in IGNORE_DIRS or item.startswith("V_") or item.startswith("."):
                    continue
                
                # 递归获取子目录的汇报
                report = self.analyze_recursive(full_path)
                if report:
                    sub_summaries.append(report)

        # 2. 扫描本级代码文件
        local_code = ""
        c_h_files = [f for f in items if f.endswith(('.c', '.h'))]
        if c_h_files:
            print(f">>> [代码分析] 正在读取模块: {current_name} ({len(c_h_files)} files)")
            for f_name in c_h_files:
                file_path = os.path.join(current_path, f_name)
                # 排除太大的文件 (例如 > 200KB)
                if os.path.getsize(file_path) > 204800:
                    print(f"    ! 跳过大文件: {f_name}")
                    continue
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f_obj:
                        local_code += f"\n// SOURCE: {f_name}\n" + f_obj.read()
                except: pass

        # 3. 决定本级文档生成策略
        current_md = ""
        base_title = f"{current_name}_LLD"
        
        # 读取历史版本（用于归档比对）
        context_md = "NONE"
        md_path = os.path.join(current_path, f"{base_title}.md")
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                context_md = f.read()

        # A. 混合层：既有代码又有子模块（例如 bsp 根目录）
        if local_code and sub_summaries:
            print(f">>> [层级汇总] 正在合并代码与子模块关系: {current_name}")
            # 将代码核心描述作为一条特殊摘要
            local_brief = f"Module [{current_name}] contains direct source code implementing core logic."
            combined_input = [local_brief] + sub_summaries
            current_md = self.ai.call_ai_parent(current_name, combined_input)

        # B. 代码层：纯代码文件夹
        elif local_code:
            print(f">>> [详细设计] 正在生成底层模块文档: {current_name}")
            # 限制发送给AI的代码长度，防止Query太大（例如截断前 60000 字符）
            safe_code = local_code[:60000]
            current_md = self.ai.call_ai(safe_code, current_name, context_md)

        # C. 逻辑组织层：仅包含子文件夹
        elif sub_summaries:
            print(f">>> [架构设计] 正在生成父目录汇总手册: {current_name}")
            current_md = self.ai.call_ai_parent(current_name, sub_summaries)

        # 4. 执行导出并返回“冒泡信息”
        if current_md:
            # 归档并生成新文件
            self.ai.archive_old_files(current_path, base_title, context_md)
            self.exporter.export(current_md, base_title, current_path)
            
            # 返回摘要给父目录。注意：这里返回给父目录的是“高维摘要”，不包含代码细节
            summary_for_parent = f"Module: {current_name}\nKey Functionality: {current_md[:450]}..."
            return summary_for_parent

        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()