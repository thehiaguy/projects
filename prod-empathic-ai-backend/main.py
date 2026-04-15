from pathlib import Path
import sys

import uvicorn


ROOT_DIR = Path(__file__).resolve().parent
API_DIR = ROOT_DIR / "apps" / "api"

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

def main():
    uvicorn.run(
        "core.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(API_DIR)],
    )


if __name__ == "__main__":
    main()
