import os
import re
import datetime
import dashscope

class DocEngine:
    def __init__(self, api_key, app_id):
        self.api_key = api_key
        self.app_id = app_id
        dashscope.api_key = api_key

    def repair_markdown_syntax(self, text):
        """修复表格前后缺失空行导致的渲染问题"""
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
        old_doc_text = f"[PREVIOUS DOCUMENT]\n{md_file_content}" if md_file_content != "NONE" else "[PREVIOUS DOCUMENT]\n(EMPTY)"
        
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
        resp = dashscope.Application.call(app_id=self.app_id, prompt=prompt)
        if resp.status_code == 200:
            return self.repair_markdown_syntax(resp.output.text)
        return f"AI Error: {resp.message}"

    def archive_old_files(self, folder, base_title, context_md):
        """安全归档旧版本文件"""
        if context_md == "NONE": return
        
        old_v_match = re.search(r'V(\d+\.\d+\.\d+)', context_md)
        old_version = f"V{old_v_match.group(1)}" if old_v_match else f"V_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        for ext in ['.md', '.html', '.pdf']:
            old_file = os.path.join(folder, f"{base_title}{ext}")
            archive_file = os.path.join(folder, f"{base_title}_{old_version}{ext}")
            if os.path.exists(old_file):
                if os.path.exists(archive_file): os.remove(archive_file)
                os.rename(old_file, archive_file)
        return old_version
    # 在 ai_engine.py 的 DocEngine 类末尾添加以下代码：

    # 父目录提示词
    def call_ai_parent(self,parent_name, summaries):
        """
        分析父目录下所有子模块的架构关系，并生成系统级文档。
        summaries: 包含各子模块名称及功能摘要的列表。
        """
        summary_text = "\n".join(summaries)
        # 核心 Prompt 设计：聚焦架构抽象与模块间协同
        prompt = f"""As a Senior System Architect, analyze the software architecture and inter-module relationships for the project: {parent_name}.
        [SUB-MODULE CONTEXT]
        The following modules were detected within the project. Each has been processed into an individual LLD:
        {summary_text}

        [ANALYSIS REQUIREMENTS]
        1. ARCHITECTURAL LAYERS: Categorize these modules into logical layers (e.g., Hardware Abstraction Layer, Middleware, Service Layer, or Application Layer).
        2. INTERACTION & DEPENDENCIES: Describe how these modules collaborate. Identify potential data flows or control logic between them.
        3. SYSTEM INTEGRATION: Summarize the overall purpose of this "Parent" block and how it functions as a unified system.

        [FORMAT GUIDELINES - STRICT ADHERENCE]
        1. Use standard Markdown structure with clear headings (##, ###).
        2. Use professional tables for module comparison and role definition.
        3. Use Mermaid flowcharts or sequence diagrams to visualize the "Architecture Map".
        4. OUTPUT ONLY IN ENGLISH.
        5. NO CHINESE. NO LaTeX.
        6. Ensure a professional, technical tone suitable for high-level technical manuals.
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
        """
        # --- 必须添加以下请求逻辑 ---
        resp = dashscope.Application.call(app_id=self.app_id, prompt=prompt)
        if resp.status_code == 200:
            return self.repair_markdown_syntax(resp.output.text)
        return f"AI Error: {resp.message}"
    
    def process_recursive(self, folder):
        """
        递归处理文件夹逻辑：
        1. 只要子文件夹有 .c/.h，父文件夹就会跟着输出汇总文档。
        2. 返回值确保为字符串 (Markdown内容)，空目录返回 None。
        """
        local_code = ""
        child_summaries = []
        curr_name = os.path.basename(folder)
        base_title = f"{curr_name}_LLD"
        
        # 1. 递归处理子文件夹
        for item in os.listdir(folder):
            it_path = os.path.join(folder, item)
            if os.path.isdir(it_path) and not item.startswith('.'):
                # 递归调用
                child_md = self.process_recursive(it_path)
                if child_md:
                    # 如果子文件夹不是空的，记录它的摘要供给父文件夹分析
                    # 提取前500字作为摘要，防止 Prompt 过长
                    summary = child_md[:500].replace('\n', ' ')
                    child_summaries.append(f"- Module [{item}]: {summary}...")

        # 2. 扫描当前文件夹的本地代码
        for f in os.listdir(folder):
            if f.endswith(('.c', '.h')):
                try:
                    with open(os.path.join(folder, f), 'r', encoding='utf-8', errors='ignore') as f_obj:
                        local_code += f"\n// FILE: {f}\n" + f_obj.read()
                except: pass

        # 3. 判定逻辑：只有当本地没代码且没有任何子模块有内容时，才判定为空壳
        if not local_code.strip() and not child_summaries:
            return None

        # 4. 生成文档
        print(f">>> 正在分析目录: {curr_name} (包含 {len(child_summaries)} 个子模块)")
        
        # 获取旧文档上下文（用于版本更新）
        context_md = "NONE"
        base_md_path = os.path.join(folder, f"{base_title}.md")
        if os.path.exists(base_md_path):
            with open(base_md_path, 'r', encoding='utf-8') as f:
                context_md = f.read()

        # 根据是否有子模块决定调用哪个提示词接口
        if child_summaries:
            # 调用你代码里定义的 call_ai_parent
            # 注意：你代码里的 call_ai_parent 缺少 return 语句，记得补上（见下方提示）
            new_md = self.call_ai_parent(curr_name, child_summaries)
        else:
            # 纯代码叶子节点
            new_md = self.call_ai(local_code, curr_name, context_md)

        # 确保返回的是字符串
        return new_md if new_md else ""

    def archive_old_files(self, folder, base_title, context_md):
        """安全归档旧版本文件"""
        if context_md == "NONE":
            return None
        
        # 提取版本号用于重命名
        old_v_match = re.search(r'V(\d+\.\d+\.\d+)', context_md)
        if old_v_match:
            old_version = f"V{old_v_match.group(1)}"
        else:
            old_version = f"V_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 将旧的 .md, .html, .pdf 重命名归档
        for ext in ['.md', '.html', '.pdf']:
            old_file = os.path.join(folder, f"{base_title}{ext}")
            archive_file = os.path.join(folder, f"{base_title}_{old_version}{ext}")
            if os.path.exists(old_file):
                if os.path.exists(archive_file):
                    os.remove(archive_file)
                os.rename(old_file, archive_file)
        return old_version