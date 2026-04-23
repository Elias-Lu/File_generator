import os
import datetime
import markdown

class ExportEngine:
    def __init__(self):
        self.PDF_SUPPORT = False
        try:
            from playwright.sync_api import sync_playwright
            self.PDF_SUPPORT = True
        except ImportError:
            pass

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

    def export(self, md_body, title, folder):
        date_str = datetime.date.today().strftime("%d-%b-%Y")
        
        # 1. 保存 Markdown
        md_path = os.path.join(folder, f"{title}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_body)
        
        # 2. 生成 HTML
        html_content = markdown.markdown(md_body, extensions=['tables', 'fenced_code', 'toc', 'sane_lists'])
        full_html = self.HTML_TEMPLATE.replace("{title}", title).replace("{date}", date_str).replace("{content}", html_content)
        html_path = os.path.join(folder, f"{title}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        # 3. 生成 PDF
        if self.PDF_SUPPORT:
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
            except Exception as e:
                print(f"PDF Error: {e}")
                