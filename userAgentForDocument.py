import os
import sys
import threading
import datetime
import re
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import markdown
import dashscope

# =================================================================
# 1. 核心配置与 API
# =================================================================
FIXED_API_KEY = "sk-f38b529997ef4760bb468d74f54f7b03"
FIXED_APP_ID = "e0cf1cac638f4a2da01973073a1ceb06"

def force_disable_proxies():
    for key in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
        if key in os.environ: del os.environ[key]
    try:
        import urllib.request
        urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))
    except: pass

force_disable_proxies()

PDF_SUPPORT = False
def init_pdf_engine():
    global PDF_SUPPORT
    try:
        from playwright.sync_api import sync_playwright
        PDF_SUPPORT = True
    except: pass

# =================================================================
# 2. HTML 渲染模板 (Schneider 样式复刻)
# =================================================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>
    window.mermaidRendered = false;
    mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });
    window.addEventListener('load', async () => {
        const blocks = document.querySelectorAll('pre code.language-mermaid, code.language-mermaid');
        blocks.forEach(block => {
            const pre = block.closest('pre');
            const div = document.createElement('div');
            div.className = 'mermaid';
            div.textContent = block.textContent;
            if (pre) { pre.parentNode.replaceChild(div, pre); }
            else { block.parentNode.replaceChild(div, block); }
        });
        try {
            await mermaid.run({ querySelector: '.mermaid' });
            setTimeout(() => { window.mermaidRendered = true; }, 1500);
        } catch (e) { window.mermaidRendered = true; }
    });
</script>
<style>
    @import "https://fonts.googleapis.com/css?family=Nunito:300,400,600,700";
    @page { size: A4; margin: 35mm 20mm 30mm 20mm; }
    html { font-family: "Nunito", sans-serif; color: #333; -webkit-print-color-adjust: exact; }
    body { margin: 0; padding: 0; line-height: 1.6; background: #fff; }
    .cover-page { height: 240mm; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; page-break-after: always; }
    .cover-label { color: #3dcd58; font-weight: 700; font-size: 15pt; letter-spacing: 2px; }
    .cover-title { font-size: 44pt; font-weight: 800; color: #000; margin: 15px 0; }
    .cover-date { color: #3dcd58; font-weight: 600; font-size: 13pt; }
    h1 { border-bottom: 3.5px solid #3dcd58; padding-bottom: 8px; margin-top: 1.8em; font-size: 24pt; color: #000; }
    h2 { color: #3dcd58; font-size: 18pt; margin-top: 1.4em; border-bottom: 1px dashed #e0e0e0; padding-bottom: 4px; }
    h3 { border-left: 6px solid #3dcd58; padding-left: 15px; font-size: 13pt; margin-top: 1.1em; color: #333; }
    table { width: 100% !important; border-collapse: collapse !important; margin: 25px 0 !important; font-size: 10pt !important; display: table !important; }
    th { background: #3dcd58 !important; color: #ffffff !important; padding: 12px !important; text-align: left !important; border: 1px solid #c8e6ca !important; }
    td { padding: 10px !important; border: 1px solid #e0e0e0 !important; }
    tr:nth-child(even) { background-color: #f9fdf9 !important; }
    pre { background: #f8f9fa; border-left: 5px solid #3dcd58; padding: 15px; border-radius: 4px; overflow-x: auto; font-family: "Consolas", monospace; font-size: 8.5pt; }
</style>
</head>
<body>
    <div class="cover-page">
        <div class="cover-label">FIRMWARE ENGINEERING</div>
        <div class="cover-title">{title}</div>
        <div class="cover-subtitle">Detailed Design Specification</div>
        <div class="cover-date">Date: {date}</div>
    </div>
    <div id="main-content">{content}</div>
</body>
</html>
"""

# =================================================================
# 3. 业务引擎类
# =================================================================
class DocEngine:
    def __init__(self):
        dashscope.api_key = FIXED_API_KEY

    def repair_markdown_syntax(self, text):
        text = text.replace("$", "")
        lines = text.split('\n')
        repaired = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('|') and i > 0 and lines[i-1].strip() != "" and not lines[i-1].strip().startswith('|'):
                repaired.append("")
            repaired.append(line)
            if stripped.startswith('|') and i < len(lines)-1 and lines[i+1].strip() != "" and not lines[i+1].strip().startswith('|'):
                repaired.append("")
        return '\n'.join(repaired)

    def call_ai(self, code, name, md_file_content="NONE"):
        # 1. 动态生成旧文档的上下文
        if md_file_content == "NONE":
            old_doc_text = "[PREVIOUS DOCUMENT]\n(EMPTY - THIS IS THE INITIAL VERSION)"
        else:
            old_doc_text = f"[PREVIOUS DOCUMENT]\n{md_file_content}"

        # 2. 组装终极 Prompt
        prompt = f"""As a Senior Firmware Architect, generate an EXHAUSTIVE Detailed Design Specification (LLD) in ENGLISH for the module: {name}.

[CRITICAL INSTRUCTIONS]
1. OUTPUT THE DOCUMENT ONLY. Do not include any conversational filler or greetings.
2. NO CHINESE. NO "SDIP" mention.
3. NO LaTeX: Never use '$' for variables. Use plain text (e.g., use 'T_wr' instead of '$T_{{wr}}$').
4. TABLES: Ensure professional Markdown tables for all registers, memory maps, and API parameters. Ensure a blank line before and after every table.
5. LOGIC: Analyze the source code and explain the ACTUAL implementation details, state machines, and physical constraints.

[VERSION CONTROL RULES - STRICT COMPLIANCE REQUIRED]
Read the [PREVIOUS DOCUMENT] section at the bottom.
- IF [PREVIOUS DOCUMENT] is empty:
  * You MUST write exactly "Version: V0.0.1" at the very top of your response.
  * In the "CHANGES" table, add a single row for V0.0.1 stating "Initial document generation."
- IF [PREVIOUS DOCUMENT] contains content:
  * Find the version number of the previous document.
  * Increment the version number by 1 (e.g., V0.0.1 becomes V0.0.2).
  * You MUST write exactly "Version: V[New_Version]" at the very top of your response.
  * Keep all previous rows in the "CHANGES" table and APPEND a new row for the new version.
  * Compare the [PREVIOUS DOCUMENT] with the [SOURCE CODE] to describe the actual changes in this new row.

[REQUIRED STRUCTURE]
Version: V[Major].[Minor].[Patch]

## 1 CHANGES
| VERSION | DATE | AUTHORS | CHANGES |
|---|---|---|---|
(Populate according to Version Control Rules)

## 2 INTRODUCTION
- 2.1 Purpose, 2.2 Scope, 2.3 Key Features.

## 3 Addressed requirement and Tracebilitys
### 3.1 Functional requirements
| Req ID | Description |
|---|---|
| FR-001 | The system shall ... |

### 3.2 Nonfunctional requirements
| Req ID | Description |
|---|---|
| NFR-001 | The system shall ... |
(NOTE: In these sections please use positive form: "The system shall ...")

## 4 WORKING PRINCIPLE AND CONSTRAINTS
- 4.1 Theory of Operation (Deep logic explanation).
- 4.2 Constraints and Limitations (Timing, Memory, Hardware boundaries).

## 5 LOGICAL DESIGN
- Narrative description + ONE 'flowchart TD' + ONE 'sequenceDiagram'.
- Use DOUBLE QUOTES for all node texts in Mermaid (e.g., A["Task Name"]).

## 6 PUBLIC INTERFACES 
(Full Tables)

## 7 PRIVATE FUNCTIONS 
(Full Tables)

## 8 IMPLEMENTATION
- 8.1 Folder Structure, 8.2 Build Integration, 8.3 Usage Example (Complete C snippet).

[SOURCE CODE]
{code}

{old_doc_text}
"""
        # 3. 发送请求给大模型
        resp = dashscope.Application.call(
            app_id=FIXED_APP_ID,
            prompt=prompt
        )
        if resp.status_code == 200:
            return self.repair_markdown_syntax(resp.output.text)
        return f"AI Error: {resp.message}"

    def export_files(self, md_body, title, folder):
        date_str = datetime.date.today().strftime("%d-%b-%Y")
        
        # 核心修改点：去掉了冗余的 _LLD，直接用传入的 title 命名
        with open(os.path.join(folder, f"{title}.md"), 'w', encoding='utf-8') as f:
            f.write(md_body)
        
        html_content = markdown.markdown(md_body, extensions=['tables', 'fenced_code', 'toc', 'sane_lists'])
        full_html = HTML_TEMPLATE.replace("{title}", title).replace("{date}", date_str).replace("{content}", html_content)
        
        html_path = os.path.join(folder, f"{title}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        if PDF_SUPPORT:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto("file:///" + os.path.abspath(html_path).replace('\\', '/'))
                    try:
                        page.wait_for_function("window.mermaidRendered === true", timeout=45000)
                        page.wait_for_timeout(1000)
                    except: pass
                    
                    h_tpl = f'<div style="font-family:Nunito;font-size:8px;width:100%;padding:0 45px;display:flex;justify-content:space-between;border-bottom:1px solid #ddd;color:#666;"><span>LLD: {title}</span><span>Schneider Electric</span></div>'
                    f_tpl = '<div style="font-family:Nunito;font-size:8px;width:100%;text-align:center;color:#666;padding-top:5px;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>'
                    
                    page.pdf(path=os.path.join(folder, f"{title}.pdf"), format="A4", print_background=True, display_header_footer=True, header_template=h_tpl, footer_template=f_tpl, margin={"top": "35mm", "bottom": "30mm"})
                    browser.close()
            except Exception as e: print(f"PDF Error: {e}")

    def process_recursive(self, folder):
        local_code = ""
        context_md = "NONE" 
        
        curr_name = os.path.basename(folder)
        base_title = f"{curr_name}_LLD"
        base_md_path = os.path.join(folder, f"{base_title}.md")

        try:
            # 1. 扫描固定名称的最新版 MD
            if os.path.exists(base_md_path):
                with open(base_md_path, 'r', encoding='utf-8') as f:
                    context_md = f.read()
                print(f">>> 发现当前最新版本文档: {base_title}.md")
            else:
                print(">>> 未发现历史文档，将作为初始版本生成...")

            # 2. 收集代码
            for f in os.listdir(folder):
                if f.endswith(('.c', '.h')):
                    with open(os.path.join(folder, f), 'r', encoding='utf-8', errors='ignore') as f_obj:
                        local_code += f"\n// FILE: {f}\n" + f_obj.read()
        except Exception as e:
            print(f"!!! 本地扫描出错: {e}")

        if not local_code: return None
        print(f">>> 正在请求 AI 分析与生成: {curr_name}...")

        # 3. 调用 AI 
        new_md_content = self.call_ai(local_code, curr_name, context_md)
        
        # 4. 安全归档：旧文档改名移走
        if context_md != "NONE":
            old_v_match = re.search(r'V(\d+\.\d+\.\d+)', context_md)
            if old_v_match:
                old_version = f"V{old_v_match.group(1)}"
            else:
                old_version = f"V_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
            for ext in ['.md', '.html', '.pdf']:
                old_file = os.path.join(folder, f"{base_title}{ext}")
                archive_file = os.path.join(folder, f"{base_title}_{old_version}{ext}")
                if os.path.exists(old_file):
                    if os.path.exists(archive_file):
                        os.remove(archive_file)
                    os.rename(old_file, archive_file)
            print(f">>> 旧版本已安全归档为: {base_title}_{old_version}")

        # 5. 输出：始终以固定名字保存最新结果
        self.export_files(new_md_content, base_title, folder)
        print(f">>> 最新版本已生成并落盘: {base_title}.pdf")
        
        return new_md_content

# =================================================================
# 4. GUI 界面
# =================================================================
class App:
    def __init__(self, root):
        self.root = root
        root.title("Technical LLD Master v14.0 (Version Control Edition)")
        root.geometry("750x650")
        f = ttk.Frame(root, padding=25); f.pack(fill="both", expand=True)
        
        ttk.Label(f, text="Source Folder:").pack(anchor="w")
        self.path = ttk.Entry(f); self.path.pack(fill="x", pady=10)
        ttk.Button(f, text="Browse", command=self.browse).pack()
        
        self.btn = tk.Button(f, text="GENERATE DOCUMENTATION", bg="#3dcd58", fg="white", font=("Arial", 11, "bold"), command=self.start, height=2)
        self.btn.pack(fill="x", pady=20)
        
        self.log = scrolledtext.ScrolledText(f, height=18, bg="#1c1c1c", fg="#3dcd58"); self.log.pack(fill="both")
        
        sys.stdout = self
        init_pdf_engine()

    def write(self, s):
        self.log.insert(tk.END, s)
        self.log.see(tk.END)
        self.log.update_idletasks() # 强制实时刷新日志

    def flush(self): pass

    def browse(self):
        p = filedialog.askdirectory()
        if p: self.path.delete(0, tk.END); self.path.insert(0, p)

    def start(self):
        if not self.path.get(): return
        self.btn.config(state="disabled")
        print(">>> Starting workflow...")
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        try:
            DocEngine().process_recursive(self.path.get().strip())
            print("\n🎉 MISSION SUCCESS. Documents and archives saved.")
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: {e}")
        finally:
            self.btn.config(state="normal")

if __name__ == "__main__":
    r = tk.Tk(); App(r); r.mainloop()