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
        root.title("Technical LLD Master v15.0 (Recursive Architecture)")
        root.geometry("750x650")
        
        self.ai = DocEngine(FIXED_API_KEY, FIXED_APP_ID)
        self.exporter = ExportEngine()

        f = ttk.Frame(root, padding=25); f.pack(fill="both", expand=True)
        ttk.Label(f, text="Select Parent Folder:").pack(anchor="w")
        
        self.path = ttk.Entry(f); self.path.pack(fill="x", pady=10)
        ttk.Button(f, text="Browse", command=self.browse).pack()
        
        self.btn = tk.Button(f, text="GENERATE ALL DOCUMENTATION", 
                             bg="#3dcd58", fg="white", font=("Arial", 11, "bold"), 
                             command=self.start)
        self.btn.pack(fill="x", pady=20)
        
        self.log = scrolledtext.ScrolledText(f, height=15, font=("Consolas", 9))
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
            print("!!! 请选择有效的路径。")
            return
        
        self.btn.config(state="disabled")
        self.log.delete(1.0, tk.END)
        threading.Thread(target=self.work, daemon=True).start()

    def process_folder(self, folder, summary_list):
        """
        处理单个文件夹。
        如果生成成功，返回 True；如果没有代码或失败，返回 False。
        """
        curr_name = os.path.basename(folder)
        base_title = f"{curr_name}_LLD"
        local_code = ""
        
        # 1. 扫描代码文件
        if not os.path.exists(folder): return False
        files = [f for f in os.listdir(folder) if f.endswith(('.c', '.h'))]
        if not files: return False 

        print(f"\n>>> [子模块处理] 正在读取目录: {curr_name}...")
        for f_name in files:
            file_path = os.path.join(folder, f_name)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f_obj:
                    local_code += f"\n// SOURCE: {f_name}\n" + f_obj.read()
            except Exception as e:
                print(f"!!! 读取失败 {f_name}: {e}")

        if not local_code.strip(): return False

        # 2. 读取历史版本
        context_md = "NONE"
        base_md_path = os.path.join(folder, f"{base_title}.md")
        if os.path.exists(base_md_path):
            try:
                with open(base_md_path, 'r', encoding='utf-8') as f:
                    context_md = f.read()
            except: pass

        # 3. AI 生成局部 LLD
        print(f">>> 正在请求 AI 分析模块细节: {curr_name}...")
        new_md = self.ai.call_ai(local_code, curr_name, context_md)
        
        # 4. 导出
        self.ai.archive_old_files(folder, base_title, context_md)
        self.exporter.export(new_md, base_title, folder)
        print(f"✅ 子模块文档已保存: {folder}/{base_title}.pdf")
        
        # 5. 存入摘要篮子
        summary_list.append(f"Module Name: {curr_name}\nFunction Summary: {new_md[:400]}...")
        return True

    def work(self):
        try:
            root_path = self.path.get().strip()
            root_name = os.path.basename(root_path)
            all_summaries = []

            print(f"🚀 --- 开始递归处理根目录: {root_name} ---")
            
            # 第一步：先看根目录下是否有代码，有则处理
            self.process_folder(root_path, all_summaries)

            # 第二步：遍历所有一级子目录并逐一处理
            for item in os.listdir(root_path):
                full_path = os.path.join(root_path, item)
                if os.path.isdir(full_path):
                    # 跳过归档目录
                    if item.startswith("V_") or item == "archive": continue
                    
                    # 关键修改：在这里调用处理函数，生成子目录文档
                    success = self.process_folder(full_path, all_summaries)
                    if not success:
                        print(f"--- 目录 {item} 中未发现代码文件，已跳过。")

            # 第三步：如果篮子里有摘要，说明有多个模块，生成父目录架构文档
            if len(all_summaries) > 0:
                print(f"\n>>> --------------------------------------")
                print(f">>> 正在进行根目录架构汇总分析: {root_name}")
                print(f">>> 汇总模块数量: {len(all_summaries)}")
                
                parent_title = f"{root_name}_LLD"
                p_context_md = "NONE"
                p_md_path = os.path.join(root_path, f"{parent_title}.md")
                if os.path.exists(p_md_path):
                    try:
                        with open(p_md_path, 'r', encoding='utf-8') as f:
                            p_context_md = f.read()
                    except: pass

                # 调用汇总接口
                parent_md = self.ai.call_ai_parent(root_name, all_summaries)
                
                # 归档并导出根目录报告
                self.ai.archive_old_files(root_path, parent_title, p_context_md)
                self.exporter.export(parent_md, parent_title, root_path)
                print(f"✅ 根目录架构报告渲染完成: {parent_title}")

            print(f"\n🎉 任务成功！所有文档已存至: {root_path}")
            
        except Exception as e:
            print(f"\n❌ 运行出错: {str(e)}")
        finally:
            self.btn.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()