import argparse
import os
import socket
import sys
import pandas as pd

from backend.logic import ExcelChecker


def main():
    if not os.environ.get("FORCE_CLI"):
        auto_web_start()
        return

    parser = argparse.ArgumentParser(
        description="Excel 数据核对工具（命令行版，无 Tkinter）"
    )
    parser.add_argument(
        "--standard",
        help="标准正确表路径（.xlsx/.xls）",
    )
    parser.add_argument(
        "--manual",
        help="人工手输表路径（.xlsx/.xls）",
    )
    parser.add_argument(
        "--output",
        help="核对结果输出路径（.xlsx）",
    )
    args = parser.parse_args()

    if not args.standard or not args.manual or not args.output:
        parser.error("命令行模式需要同时提供 --standard --manual --output")

    if not os.path.exists(args.standard):
        print(f"标准正确表不存在: {args.standard}", file=sys.stderr)
        sys.exit(2)
    if not os.path.exists(args.manual):
        print(f"人工手输表不存在: {args.manual}", file=sys.stderr)
        sys.exit(2)

    checker = ExcelChecker(log_fn=print)
    try:
        standard_df = pd.read_excel(args.standard)
    except Exception as exc:
        print(f"读取标准正确表失败: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        manual_df = pd.read_excel(args.manual)
    except Exception as exc:
        print(f"读取人工手输表失败: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        result_df = checker.compare_data(standard_df, manual_df)
    except Exception as exc:
        print(f"核对失败: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        result_df.to_excel(args.output, index=False)
        print(f"核对完成，结果已保存: {args.output}")
    except Exception as exc:
        print(f"保存结果失败: {exc}", file=sys.stderr)
        sys.exit(2)


def get_lan_host():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def auto_web_start():
    import webbrowser
    from subprocess import Popen

    root = os.path.dirname(os.path.abspath(__file__))
    backend_app = os.path.join(root, "backend", "app.py")
    frontend_dir = os.path.join(root, "frontend")

    backend_env = os.environ.copy()
    backend_env.setdefault("HOST", "0.0.0.0")
    backend_env.setdefault("PORT", "5051")

    Popen([sys.executable, backend_app], env=backend_env)
    Popen([sys.executable, "-m", "http.server", "8081", "--bind", "0.0.0.0"], cwd=frontend_dir)

    lan_host = get_lan_host()
    print(f"本机访问地址: http://127.0.0.1:8081")
    print(f"局域网访问地址: http://{lan_host}:8081")
    print(f"局域网后端地址: http://{lan_host}:5051")
    webbrowser.open("http://127.0.0.1:8081")


if __name__ == "__main__":
    main()
