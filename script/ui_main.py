# ui_main.py
import os
import sys
import re
import threading
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from ai_engine import DocEngine
from export_engine import ExportEngine

FIXED_API_KEY = "sk-f38b529997ef4760bb468d74f54f7b03"
FIXED_APP_ID = "e0cf1cac638f4a2da01973073a1ceb06"

IGNORE_DIRS = {
    "build", "Debug", "Release", "bin", "obj",
    ".git", ".svn", ".vscode", ".idea",
    "archive", "Output", "Document"
}

class App:
    def __init__(self, root):
        self.root = root
        root.title("Technical LLD Master v18.0 (Separated Generation)")
        root.geometry("850x750")

        self.ai = DocEngine(FIXED_API_KEY, FIXED_APP_ID)
        self.exporter = ExportEngine()

        f = ttk.Frame(root, padding=25)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Select Root Project Folder:").pack(anchor="w")
        self.path = ttk.Entry(f)
        self.path.pack(fill="x", pady=10)
        ttk.Button(f, text="Browse", command=self.browse).pack()

        # Requirements 文件选择
        req_frame = ttk.Frame(f)
        req_frame.pack(fill="x", pady=10)
        ttk.Label(req_frame, text="Requirements Excel File (Optional):").pack(anchor="w")
        self.req_path = ttk.Entry(req_frame)
        self.req_path.pack(fill="x", pady=5)
        ttk.Button(req_frame, text="Browse XLSX", command=self.browse_req).pack()

        # 三个独立按钮
        btn_frame = ttk.Frame(f)
        btn_frame.pack(fill="x", pady=15)
        self.btn_md = tk.Button(btn_frame, text="1. Generate MD (Two‑Level LLD)", bg="#3dcd58", fg="white",
                                font=("Arial", 10, "bold"), command=self.start_md_generation)
        self.btn_md.pack(side="left", padx=5, expand=True, fill="x")
        self.btn_html = tk.Button(btn_frame, text="2. Generate HTML from MDs", bg="#2196f3", fg="white",
                                  font=("Arial", 10, "bold"), command=self.start_html_generation)
        self.btn_html.pack(side="left", padx=5, expand=True, fill="x")
        self.btn_pdf = tk.Button(btn_frame, text="3. Generate PDF from HTMLs", bg="#ff9800", fg="white",
                                 font=("Arial", 10, "bold"), command=self.start_pdf_generation)
        self.btn_pdf.pack(side="left", padx=5, expand=True, fill="x")

        self.log = scrolledtext.ScrolledText(f, height=18, font=("Consolas", 10))
        self.log.pack(fill="both", expand=True)

        sys.stdout = self

        self.root_path = None
        self.doc_root = None
        self.md_root = None
        self.html_root = None
        self.pdf_root = None

    def write(self, txt):
        if txt:
            self.log.insert(tk.END, str(txt))
            self.log.see(tk.END)

    def flush(self):
        pass

    def browse(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path.delete(0, tk.END)
            self.path.insert(0, directory)

    def browse_req(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            self.req_path.delete(0, tk.END)
            self.req_path.insert(0, file_path)

    # ------------------- 通用辅助方法 -------------------
    def set_buttons_state(self, state):
        self.btn_md.config(state=state)
        self.btn_html.config(state=state)
        self.btn_pdf.config(state=state)

    def get_all_source_code(self, directory):
        code = ""
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for f in files:
                if f.endswith(('.c', '.h')):
                    file_path = os.path.join(root, f)
                    if os.path.getsize(file_path) > 204800:
                        print(f"    ! Skipping large file: {file_path}")
                        continue
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
                            rel_path = os.path.relpath(file_path, directory)
                            code += f"\n// FILE: {rel_path}\n" + fp.read()
                    except Exception as e:
                        print(f"    ! Error reading {file_path}: {e}")
        return code

    def load_requirements_from_xlsx(self, xlsx_path):
        """从 xlsx 文件中读取 requirements 表格"""
        try:
            import pandas as pd
            df = pd.read_excel(xlsx_path, engine='openpyxl')
            
            req_text = "\n\n## Requirements from Specifications\n\n"
            req_text += "### Functional Requirements\n"
            req_text += "| Req ID | Description |\n"
            req_text += "|--------|-------------|\n"
            
            # 尝试找到 ID 和 Description 列
            id_col = None
            desc_col = None
            for col in df.columns:
                if 'id' in col.lower() or 'req' in col.lower():
                    id_col = col
                if 'desc' in col.lower() or 'requirement' in col.lower():
                    desc_col = col
            
            if id_col is None:
                id_col = df.columns[0]
            if desc_col is None:
                desc_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            
            for _, row in df.iterrows():
                req_id = row[id_col]
                desc = row[desc_col]
                req_text += f"| {req_id} | {desc} |\n"
            
            print(f"✅ Loaded {len(df)} requirements from {xlsx_path}")
            return req_text
        except Exception as e:
            print(f"❌ Failed to load requirements: {e}")
            return ""

    def archive_old_file(self, file_path, context_md):
        if not os.path.exists(file_path) or context_md == "NONE":
            return
        v_match = re.search(r'V(\d+\.\d+\.\d+)', context_md)
        if v_match:
            version = f"V{v_match.group(1)}"
        else:
            version = f"V_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        base, ext = os.path.splitext(file_path)
        archive_path = f"{base}_{version}{ext}"
        if os.path.exists(archive_path):
            os.remove(archive_path)
        os.rename(file_path, archive_path)
        print(f"    Archived old file -> {os.path.basename(archive_path)}")

    def update_index_file(self):
        """在根目录生成 LLD_Index.html，包含所有文档的超链接"""
        if not self.root_path:
            return
        index_path = os.path.join(self.root_path, "LLD_Index.html")
        # 收集所有文档
        entries = []
        
        # 架构文档直接放在 Document 目录下
        arch_md = os.path.join(self.doc_root, "LLD_Architecture.md")
        if os.path.exists(arch_md):
            arch_html = os.path.join(self.doc_root, "LLD_Architecture.html")
            if os.path.exists(arch_html):
                entries.append(("LLD_Architecture (Top Architecture)", "Document/LLD_Architecture.html"))
            else:
                entries.append(("LLD_Architecture (Top Architecture)", "Document/LLD_Architecture.md"))
        
        # 子模块文档 (Document/md/*.md)
        if self.md_root and os.path.exists(self.md_root):
            for md_file in os.listdir(self.md_root):
                if md_file.endswith(".md"):
                    title = md_file[:-3]
                    html_path = os.path.join(self.html_root, f"{title}.html") if self.html_root else None
                    if html_path and os.path.exists(html_path):
                        entries.append((title, f"Document/html/{title}.html"))
                    else:
                        entries.append((title, f"Document/md/{md_file}"))
        
        # 生成 HTML 索引
        html_content = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>LLD Document Index</title>
<style>
    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
    .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #3dcd58; border-bottom: 3px solid #3dcd58; padding-bottom: 10px; }
    ul { list-style: none; padding: 0; }
    li { margin: 15px 0; padding: 10px; background: #f9f9f9; border-radius: 5px; transition: all 0.3s; }
    li:hover { background: #e8f5e9; transform: translateX(5px); }
    a { text-decoration: none; color: #2c7da0; font-size: 16px; font-weight: 500; }
    a:hover { text-decoration: underline; color: #3dcd58; }
    .badge { display: inline-block; background: #3dcd58; color: white; font-size: 12px; padding: 2px 8px; border-radius: 12px; margin-left: 10px; }
</style>
</head>
<body>
<div class="container">
    <h1>📚 Generated LLD Documents</h1>
    <p>Below is the complete list of generated Low-Level Design documents:</p>
    <ul>
"""
        for name, link in entries:
            # 判断是 HTML 还是 MD
            badge = '<span class="badge">HTML</span>' if 'html' in link else '<span class="badge">MD</span>'
            html_content += f'<li><a href="{link}" target="_blank">{name}</a> {badge}</li>\n'
        html_content += """
    </ul>
    <hr>
    <p style="color: #666; font-size: 12px; text-align: center;">Generated by Technical LLD Master v18.0</p>
</div>
</body>
</html>"""
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Index file updated: {index_path}")

    # ------------------- MD 生成（仅大模型） -------------------
    def analyze_two_level_md_only(self, current_path, depth):
        """递归生成 MD 文档（不转换 HTML/PDF）"""
        current_name = os.path.basename(current_path)
        print(f"{'  ' * depth}Processing: {current_name} (depth={depth})")
        sub_summaries = []

        if depth == 0:
            # 处理子模块
            try:
                items = os.listdir(current_path)
            except:
                return None
            for item in items:
                child_path = os.path.join(current_path, item)
                if os.path.isdir(child_path) and item not in IGNORE_DIRS and not item.startswith('.'):
                    summary = self.analyze_two_level_md_only(child_path, depth + 1)
                    if summary:
                        sub_summaries.append(summary)

            if sub_summaries:
                print(f">>> Generating root architecture MD: {current_name}")
                context_md = "NONE"
                title = "LLD_Architecture"  # 固定名称
                # 架构文档直接放在 Document 目录下
                md_path = os.path.join(self.doc_root, f"{title}.md")
                
                # 加载 requirements
                req_content = ""
                req_file = self.req_path.get().strip() if hasattr(self, 'req_path') else ""
                if req_file and os.path.exists(req_file):
                    req_content = self.load_requirements_from_xlsx(req_file)
                
                if os.path.exists(md_path):
                    with open(md_path, 'r', encoding='utf-8') as f:
                        context_md = f.read()
                
                self.archive_old_file(md_path, context_md)
                # 调用 AI，传入 requirements
                new_md = self.ai.call_ai_parent(current_name, sub_summaries, req_content)
                if new_md:
                    self.exporter.save_md_only(new_md, md_path)
                    return f"Module: {current_name}\nKey Functionality: {new_md[:450]}..."
            return None

        elif depth == 1:
            print(f">>> Generating detailed MD for leaf module: {current_name}")
            all_code = self.get_all_source_code(current_path)
            if not all_code.strip():
                print(f"    Warning: No .c/.h files under {current_name}, skipping.")
                return None
            title = f"LLD_{current_name}"
            md_path = os.path.join(self.md_root, f"{title}.md")
            context_md = "NONE"
            if os.path.exists(md_path):
                with open(md_path, 'r', encoding='utf-8') as f:
                    context_md = f.read()
            self.archive_old_file(md_path, context_md)
            safe_code = all_code[:60000]
            new_md = self.ai.call_ai(safe_code, current_name, context_md)
            if new_md:
                self.exporter.save_md_only(new_md, md_path)
                return f"Module: {current_name}\nKey Functionality: {new_md[:450]}..."
            return None
        else:
            return None

    def start_md_generation(self):
        folder = self.path.get().strip()
        if not folder or not os.path.exists(folder):
            print("!!! Please select a valid project root directory.")
            return
        self.root_path = folder
        self.doc_root = os.path.join(self.root_path, "Document")
        self.md_root = os.path.join(self.doc_root, "md")
        self.html_root = os.path.join(self.doc_root, "html")
        self.pdf_root = os.path.join(self.doc_root, "pdf")
        os.makedirs(self.md_root, exist_ok=True)
        os.makedirs(self.html_root, exist_ok=True)
        os.makedirs(self.pdf_root, exist_ok=True)

        self.set_buttons_state("disabled")
        self.log.delete(1.0, tk.END)
        threading.Thread(target=self._md_work, daemon=True).start()

    def _md_work(self):
        try:
            print(f"🚀 Starting MD generation (AI only, no HTML/PDF)")
            self.analyze_two_level_md_only(self.root_path, depth=0)
            self.update_index_file()
            print(f"\n🎉 MD generation complete. Index: {os.path.join(self.root_path, 'LLD_Index.html')}")
        except Exception as e:
            print(f"\n❌ Critical error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.set_buttons_state("normal")

    # ------------------- HTML 生成（从已有 MD） -------------------
    def generate_html_from_all_mds(self):
        if not self.root_path:
            print("!!! Root path not set. Please generate MD first.")
            return
        
        # 确保目录存在
        if not self.html_root:
            self.html_root = os.path.join(self.doc_root, "html")
        os.makedirs(self.html_root, exist_ok=True)
        
        # 架构文档 HTML - 从 Document 目录读取，输出到 Document 目录
        arch_md = os.path.join(self.doc_root, "LLD_Architecture.md")
        arch_html = os.path.join(self.doc_root, "LLD_Architecture.html")
        if os.path.exists(arch_md):
            print("Generating HTML for LLD_Architecture...")
            self.exporter.md_to_html(arch_md, arch_html)
        else:
            print("No LLD_Architecture.md found in Document/")
        
        # 子模块 HTML 仍在 Document/md -> Document/html
        if not self.md_root or not os.path.exists(self.md_root):
            print("No Document/md folder found.")
            return
        
        for md_file in os.listdir(self.md_root):
            if md_file.endswith(".md"):
                md_path = os.path.join(self.md_root, md_file)
                html_name = md_file[:-3] + ".html"
                html_path = os.path.join(self.html_root, html_name)
                print(f"   Converting {md_file} -> HTML")
                self.exporter.md_to_html(md_path, html_path)
        
        self.update_index_file()
        print("✅ All HTML files generated.")

    def start_html_generation(self):
        if not self.root_path:
            print("!!! Root path not set. Please generate MD first.")
            return
        self.set_buttons_state("disabled")
        self.log.delete(1.0, tk.END)
        threading.Thread(target=self._html_work, daemon=True).start()

    def _html_work(self):
        try:
            self.generate_html_from_all_mds()
        except Exception as e:
            print(f"\n❌ HTML generation error: {str(e)}")
        finally:
            self.set_buttons_state("normal")

    # ------------------- PDF 生成（从已有 HTML） -------------------
    def generate_pdf_from_all_htmls(self):
        if not self.exporter.PDF_SUPPORT:
            print("!!! Playwright not installed. Install with: pip install playwright && playwright install chromium")
            return
        if not self.root_path:
            print("!!! Root path not set.")
            return
        
        # 确保目录存在
        if not self.pdf_root:
            self.pdf_root = os.path.join(self.doc_root, "pdf")
        os.makedirs(self.pdf_root, exist_ok=True)
        
        # 架构文档 PDF - 从 Document 目录读取
        arch_html = os.path.join(self.doc_root, "LLD_Architecture.html")
        arch_pdf = os.path.join(self.doc_root, "LLD_Architecture.pdf")
        if os.path.exists(arch_html):
            print("Generating PDF for LLD_Architecture...")
            self.exporter.html_to_pdf(arch_html, arch_pdf)
        else:
            print("No LLD_Architecture.html found in Document/")
        
        # 子模块 PDF 仍在 Document/html -> Document/pdf
        html_dir = os.path.join(self.doc_root, "html")
        pdf_dir = os.path.join(self.doc_root, "pdf")
        if not os.path.exists(html_dir):
            print("No Document/html folder found. Please generate HTML first.")
            return
        os.makedirs(pdf_dir, exist_ok=True)
        for html_file in os.listdir(html_dir):
            if html_file.endswith(".html"):
                html_path = os.path.join(html_dir, html_file)
                pdf_name = html_file[:-5] + ".pdf"
                pdf_path = os.path.join(pdf_dir, pdf_name)
                print(f"   Converting {html_file} -> PDF")
                self.exporter.html_to_pdf(html_path, pdf_path)
        
        self.update_index_file()
        print("✅ All PDF files generated.")

    def start_pdf_generation(self):
        if not self.root_path:
            print("!!! Root path not set. Please generate MD/HTML first.")
            return
        self.set_buttons_state("disabled")
        self.log.delete(1.0, tk.END)
        threading.Thread(target=self._pdf_work, daemon=True).start()

    def _pdf_work(self):
        try:
            self.generate_pdf_from_all_htmls()
        except Exception as e:
            print(f"\n❌ PDF generation error: {str(e)}")
        finally:
            self.set_buttons_state("normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()