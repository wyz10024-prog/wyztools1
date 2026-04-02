import io
import os
import uuid
from datetime import datetime

import pandas as pd
from flask import Flask, request, send_file, jsonify, make_response

from logic import ExcelChecker


def create_app():
    app = Flask(__name__)
    result_store = {}

    @app.after_request
    def add_cors_headers(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/compare", methods=["POST", "OPTIONS"])
    def compare():
        if request.method == "OPTIONS":
            return make_response("", 204)

        standard = request.files.get("standard")
        manual = request.files.get("manual")
        if not standard or not manual:
            return jsonify({"error": "请同时上传标准正确表和人工手输表。"}), 400

        logs = []
        checker = ExcelChecker(log_fn=logs.append)

        try:
            standard_df = pd.read_excel(standard)
        except Exception as exc:
            return jsonify({"error": f"读取标准正确表失败: {exc}"}), 400

        try:
            manual_df = pd.read_excel(manual)
        except Exception as exc:
            return jsonify({"error": f"读取人工手输表失败: {exc}"}), 400

        try:
            result_df = checker.compare_data(standard_df, manual_df)
        except Exception as exc:
            return jsonify({"error": f"核对失败: {exc}"}), 400

        output = io.BytesIO()
        result_df.to_excel(output, index=False)
        output.seek(0)
        token = str(uuid.uuid4())
        result_store[token] = output.getvalue()

        summary = result_df["核对状态"].value_counts().to_dict()
        return jsonify(
            {
                "token": token,
                "download_url": f"/api/download/{token}",
                "summary": summary,
                "logs": logs,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            }
        )

    @app.route("/api/download/<token>", methods=["GET"])
    def download(token):
        data = result_store.get(token)
        if data is None:
            return jsonify({"error": "结果不存在或已过期"}), 404
        return send_file(
            io.BytesIO(data),
            as_attachment=True,
            download_name="核对结果.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    return app


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5051"))
    app = create_app()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
