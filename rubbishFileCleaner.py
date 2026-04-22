import os
import sys
import threading
import re
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox

class CleanerApp:
    def __init__(self, root):
        self.root = root
        root.title("LLD Cleanup Utility v1.0")
        root.geometry("650x550")
        f = ttk.Frame(root, padding=25); f.pack(fill="both", expand=True)
        
        ttk.Label(f, text="Target Folder to Clean:").pack(anchor="w")
        self.path = ttk.Entry(f); self.path.pack(fill="x", pady=10)
        ttk.Button(f, text="Browse", command=self.browse).pack()
        
        # 使用醒目的红色按钮，警示这是一个删除操作
        self.btn = tk.Button(f, text="🧹 CLEAN DOCUMENTS", bg="#e53935", fg="white", font=("Arial", 11, "bold"), command=self.start, height=2)
        self.btn.pack(fill="x", pady=20)
        
        # 日志框文字也设为红色
        self.log = scrolledtext.ScrolledText(f, height=15, bg="#1c1c1c", fg="#ff8a80"); self.log.pack(fill="both")
        
        sys.stdout = self

    def write(self, s):
        self.log.insert(tk.END, s)
        self.log.see(tk.END)
        self.log.update_idletasks() # 强制实时刷新日志

    def flush(self): pass

    def browse(self):
        p = filedialog.askdirectory()
        if p: self.path.delete(0, tk.END); self.path.insert(0, p)

    def start(self):
        target_dir = self.path.get().strip()
        if not target_dir: return

        # ==========================================
        # 安全机制：执行删除前的弹窗二次确认！
        # ==========================================
        confirm_msg = f"Are you sure you want to PERMANENTLY DELETE all generated LLDs and archives in:\n\n{target_dir}\n\nThis cannot be undone!"
        if not messagebox.askyesno("⚠️ DANGER: Confirm Deletion", confirm_msg):
            print(">>> 🛑 Cleanup aborted by user.")
            return

        self.btn.config(state="disabled")
        print(">>> --------------------------------------")
        print(f">>> 🔍 Scanning for LLD documents in: {target_dir}")
        print(">>> --------------------------------------")
        
        # 启动后台线程执行删除，防止界面卡死
        threading.Thread(target=self.work, args=(target_dir,), daemon=True).start()

    def work(self, root_path):
        try:
            # 严格匹配我们生成的文件格式
            target_patterns = [
                r".*_LLD\.md$",
                r".*_LLD\.html$",
                r".*_LLD\.pdf$",
                r".*_LLD_V\d+\.\d+\.\d+\..*$", # 匹配 V0.0.1 备份
                r".*_LLD_\d{8}_\d{6}\..*$"     # 匹配 时间戳 备份
            ]

            deleted_count = 0
            
            # 递归遍历所有子目录寻找靶标
            for root, dirs, files in os.walk(root_path):
                for file in files:
                    is_target = False
                    for pattern in target_patterns:
                        if re.match(pattern, file):
                            is_target = True
                            break
                    
                    if is_target:
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            print(f"[DELETED] {file_path}")
                            deleted_count += 1
                        except Exception as e:
                            print(f"[ERROR] Failed to delete {file_path}: {e}")

            print(">>> --------------------------------------")
            print(f">>> ✅ Cleanup complete! {deleted_count} files removed.")
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: {e}")
        finally:
            self.btn.config(state="normal")

if __name__ == "__main__":
    r = tk.Tk()
    App = CleanerApp(r)
    r.mainloop()