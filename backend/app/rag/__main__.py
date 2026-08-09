"""知识库索引构建命令（备用入口）。

用法（在 backend 目录下）：
    python -m app.rag            # 等价于 python -m app.rag.build_index
"""

import sys

from app.rag.build_index import run


if __name__ == "__main__":
    # 透传命令行参数（如 --online）
    run(
        online="--online" in sys.argv,
        with_inspiration="--with-inspiration" in sys.argv,
    )
