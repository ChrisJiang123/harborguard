"""pytest 根配置：把仓库根加入 sys.path，使 `import ml...` / `import agent...` 生效。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
