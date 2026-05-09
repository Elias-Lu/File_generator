# test_prompt.py
import dashscope

# === 请替换为你的真实凭证 ===
API_KEY = "sk-f38b529997ef4760bb468d74f54f7b03"
APP_ID = "e0cf1cac638f4a2da01973073a1ceb06"

def test_call_ai_prompt():
    # 模拟一个极简的 code 内容（长度可控）
    code_sample = """
    // FILE: test.c
    void init_system(void) {
        // initialize hardware
    }

    int read_temperature(void) {
        return 25;
    }
    """

    name = "TestModule"
    old_doc = "NONE"   # 没有旧文档，首次生成

    # 复制自 ai_engine.py 中的 prompt 构造（略作简化，保留关键结构）
    old_doc_text = "[PREVIOUS DOCUMENT]\n(EMPTY)" if old_doc == "NONE" else f"[PREVIOUS DOCUMENT]\n{old_doc}"

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

[CATALOG RULES]
## CATALOG
- Generate an automatic table of contents that lists all sections (## headings) and subsections (### headings).
- Each entry MUST be a Markdown link pointing to the corresponding heading anchor (e.g., `[1 CHANGES](#1-changes)`).
- Place this TOC immediately after the "Version: VX.X.X" line, before "## 1 CHANGES".
- DO NOT include the TOC itself or the Version line in the TOC.
- Use the exact heading text (without the leading hashes) as the link text.
- Ensure that the TOC is complete and accurate based on the actual headings present in the final document.

[REQUIRED STRUCTURE]
Version: V[Major].[Minor].[Patch]

## 1 CHANGES
| VERSION | DATE | AUTHORS | CHANGES |
|---|---|---|---|
(Populate according to Version Control Rules)

IF THERE ARE NO INSTRUCTIONS OF THE DATE IN THE CODE, THE DATE SHOULD BE THE CURRENT DATE, ELSE YOU JUST FOLLOW THE INSTRUCTIONS.
IF THERE ARE NO AUTHORS IN THE INSTRUCTIONS, JUST WRITE KNOWN.

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
{code_sample}

{old_doc_text}
"""

    print(f"Prompt length: {len(prompt)} characters")
    print("Calling DashScope Application...")
    resp = dashscope.Application.call(
        app_id=APP_ID,
        prompt=prompt,
        api_key=API_KEY   # 注意：dashscope.api_key 需要提前设置，或者在这里显式传递
    )
    # 也可以提前设置：dashscope.api_key = API_KEY
    print(f"Status code: {resp.status_code}")
    print(f"Message: {resp.message}")
    if resp.status_code == 200:
        print("Response text (first 1000 chars):")
        print(resp.output.text[:1000])
    else:
        print("Full response:", resp)

if __name__ == "__main__":
    # 设置 API Key（全局）
    dashscope.api_key = API_KEY
    test_call_ai_prompt()