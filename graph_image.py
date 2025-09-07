from pathlib import Path
from langchain_core.runnables.graph import MermaidDrawMethod
from agent import ATPagent

agent = ATPagent()

png_bytes = agent.graph.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.API,
)

# 파일로 저장
out_path = Path("graph.png")
out_path.write_bytes(png_bytes)

print(f"Saved: {out_path.resolve()}")