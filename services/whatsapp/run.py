"""Inicialização local: python -m services.whatsapp.run."""
import argparse
import os
from pathlib import Path


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip().isidentifier():
            raise ValueError("Linha inválida no arquivo de configuração do gateway.")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gateway WhatsApp do Peticas")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    load_env(Path(__file__).with_name(".env"))
    import uvicorn
    uvicorn.run("services.whatsapp.app:app", host=args.host, port=args.port, access_log=False)
