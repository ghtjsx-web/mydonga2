"""
mymathjeju_structure.py
- mymathjeju_structure.md 및 mymathjeju_expert_structure.md 내의 Mermaid 다이어그램을
  자동으로 추출하여 images2 폴더에 고화질 PNG 및 SVG 이미지로 저장하는 유틸리티 스크립트.
"""

import os
import re
import sys
import base64
import requests

# Windows 터미널 출력 인코딩 UTF-8 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def render_and_save_mermaid(md_file_path: str, output_dir: str, prefix: str = ""):
    """마크다운 파일에서 Mermaid 코드 블록을 추출하여 PNG 및 SVG 파일로 저장"""
    if not os.path.exists(md_file_path):
        print(f"⚠️ 파일이 존재하지 않습니다: {md_file_path}")
        return

    os.makedirs(output_dir, exist_ok=True)

    with open(md_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    mermaid_blocks = re.findall(r'```mermaid\s*\n(.*?)```', content, re.DOTALL)
    print(f"\n🔍 [{os.path.basename(md_file_path)}] -> {len(mermaid_blocks)}개의 Mermaid 다이어그램 발견")

    for idx, block in enumerate(mermaid_blocks, 1):
        clean_code = block.strip()
        base_name = f"{prefix}_diagram_{idx}" if prefix else f"diagram_{idx}"
        
        # 첫 줄이나 헤더 분석하여 직관적인 파일명 부여
        first_line = clean_code.split('\n')[0].strip()
        if "classDiagram" in first_line:
            base_name = f"{prefix}_class_architecture"
        elif "stateDiagram" in first_line:
            base_name = f"{prefix}_state_transition"
        elif "sequenceDiagram" in first_line:
            base_name = f"{prefix}_sequence_diagram"
        elif "flowchart" in first_line:
            base_name = f"{prefix}_system_flowchart"

        # Base64 인코딩
        graphbytes = clean_code.encode("utf-8")
        base64_str = base64.b64encode(graphbytes).decode("ascii")

        # 1. PNG 이미지 다운로드 및 저장
        png_url = f"https://mermaid.ink/img/{base64_str}?type=png"
        try:
            r_png = requests.get(png_url, timeout=20)
            if r_png.status_code == 200:
                png_path = os.path.join(output_dir, f"{base_name}.png")
                with open(png_path, "wb") as f:
                    f.write(r_png.content)
                print(f"  ✅ [PNG] 저장 완료: {png_path} ({len(r_png.content):,} bytes)")
            else:
                print(f"  ❌ [PNG 실패 ({r_png.status_code})]: {base_name}")
        except Exception as e:
            print(f"  ❌ [PNG 에러]: {e}")

        # 2. SVG 벡터 이미지 다운로드 및 저장
        svg_url = f"https://mermaid.ink/svg/{base64_str}"
        try:
            r_svg = requests.get(svg_url, timeout=20)
            if r_svg.status_code == 200:
                svg_path = os.path.join(output_dir, f"{base_name}.svg")
                with open(svg_path, "wb") as f:
                    f.write(r_svg.content)
                print(f"  ✅ [SVG] 저장 완료: {svg_path} ({len(r_svg.content):,} bytes)")
            else:
                print(f"  ❌ [SVG 실패 ({r_svg.status_code})]: {base_name}")
        except Exception as e:
            print(f"  ❌ [SVG 에러]: {e}")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    images2_dir = os.path.join(base_dir, "images2")

    print("=" * 60)
    print("🎨 Mermaid 다이어그램 이미지 자동 생성 및 저장 도구")
    print(f"📂 대상 저장 폴더: {images2_dir}")
    print("=" * 60)

    # 1. 초보자용 가이드 다이어그램 추출
    beginner_md = os.path.join(base_dir, "mymathjeju_structure.md")
    render_and_save_mermaid(beginner_md, images2_dir, prefix="mymathjeju_beginner")

    # 2. 전문가용 가이드 다이어그램 추출
    expert_md = os.path.join(base_dir, "mymathjeju_expert_structure.md")
    render_and_save_mermaid(expert_md, images2_dir, prefix="mymathjeju_expert")

    print("\n🎉 모든 다이어그램이 images2 폴더에 성공적으로 저장되었습니다!")


if __name__ == "__main__":
    main()
