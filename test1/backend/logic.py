import re
import unicodedata
import pandas as pd
from difflib import SequenceMatcher


class ExcelChecker:
    def __init__(self, log_fn=None):
        self.log_fn = log_fn or (lambda msg: None)

    def log(self, msg):
        self.log_fn(msg)

    def compare_data(self, standard_df, manual_df):
        std_name_col = self.find_product_name_column(standard_df.columns)
        man_name_col = self.find_product_name_column(manual_df.columns)

        if not std_name_col or not man_name_col:
            raise ValueError("两表必须包含可识别的产品名称相关列。")

        self.log("标准正确表列名:")
        self.log(", ".join(standard_df.columns.astype(str)))
        self.log("人工手输表列名:")
        self.log(", ".join(manual_df.columns.astype(str)))

        std_raw_name_series = standard_df[std_name_col].astype(str).str.strip()
        man_raw_name_series = manual_df[man_name_col].astype(str).str.strip()

        std_key_series = std_raw_name_series.map(self.normalize_product_key)
        man_key_series = man_raw_name_series.map(self.normalize_product_key)

        std_duplicate_groups = self.find_duplicate_groups(
            std_raw_name_series, std_key_series
        )
        man_duplicate_groups = self.find_duplicate_groups(
            man_raw_name_series, man_key_series
        )

        duplicate_rows = []
        if std_duplicate_groups:
            duplicate_rows.extend(
                self.build_duplicate_result_rows(std_duplicate_groups, "标准正确表")
            )
        if man_duplicate_groups:
            duplicate_rows.extend(
                self.build_duplicate_result_rows(man_duplicate_groups, "人工手输表")
            )

        std_duplicate_keys = {group["key"] for group in std_duplicate_groups}
        man_duplicate_keys = {group["key"] for group in man_duplicate_groups}

        std_map = standard_df.loc[~std_key_series.isin(std_duplicate_keys)].copy()
        std_map["__key__"] = std_key_series[~std_key_series.isin(std_duplicate_keys)]
        man_map = manual_df.loc[~man_key_series.isin(man_duplicate_keys)].copy()
        man_map["__key__"] = man_key_series[~man_key_series.isin(man_duplicate_keys)]

        std_map["__raw_name__"] = std_raw_name_series[~std_key_series.isin(std_duplicate_keys)]
        man_map["__raw_name__"] = man_raw_name_series[~man_key_series.isin(man_duplicate_keys)]

        std_keys = set(std_map["__key__"])
        man_keys = set(man_map["__key__"])

        missing_keys = std_keys - man_keys

        matched_cols = self.match_columns(
            standard_df.columns, manual_df.columns, std_name_col, man_name_col
        )

        result_rows = list(duplicate_rows)
        for key in std_map["__key__"]:
            std_row = std_map.loc[std_map["__key__"] == key].iloc[0]
            if key in missing_keys:
                result_rows.append(
                    {
                        "产品名称": std_row["__raw_name__"],
                        "核对状态": "缺失",
                        "差异说明": "产品缺失",
                    }
                )
                continue

            man_row = man_map.loc[man_map["__key__"] == key].iloc[0]

            diffs = []
            for std_col, man_col in matched_cols.items():
                std_val = "" if pd.isna(std_row[std_col]) else str(std_row[std_col]).strip()
                man_val = "" if pd.isna(man_row[man_col]) else str(man_row[man_col]).strip()
                if not self.values_match(std_val, man_val):
                    diffs.append(
                        f"{std_col} 不一致：标准值[{std_val}] 录入值[{man_val}]"
                    )

            if diffs:
                result_rows.append(
                    {
                        "产品名称": std_row["__raw_name__"],
                        "核对状态": "不一致",
                        "差异说明": "；".join(diffs),
                    }
                )
            else:
                result_rows.append(
                    {
                        "产品名称": std_row["__raw_name__"],
                        "核对状态": "一致",
                        "差异说明": "",
                    }
                )

        return pd.DataFrame(result_rows)

    def find_duplicate_groups(self, raw_name_series, key_series):
        duplicate_keys = key_series[key_series.duplicated(keep=False)].drop_duplicates()
        groups = []
        for key in duplicate_keys:
            rows = []
            for idx, raw_name in raw_name_series[key_series == key].items():
                rows.append({"row_number": idx + 2, "raw_name": raw_name})
            groups.append({"key": key, "rows": rows})
        return groups

    def build_duplicate_result_rows(self, duplicate_groups, table_name):
        result_rows = []
        for group in duplicate_groups:
            row_labels = [
                f"第{row['row_number']}行[{row['raw_name']}]"
                for row in group["rows"]
            ]
            result_rows.append(
                {
                    "产品名称": group["rows"][0]["raw_name"],
                    "核对状态": "重复",
                    "差异说明": f"{table_name}产品名称重复：{'、'.join(row_labels)}",
                }
            )
        return result_rows

    def find_product_name_column(self, columns):
        candidates = [
            "产品名称",
            "产品名",
            "品名",
            "商品名称",
            "商品名",
            "product name",
            "product_name",
            "product",
            "name",
        ]
        for col in columns:
            col_str = str(col).strip().lower()
            for cand in candidates:
                if cand in col_str:
                    return col
        return None

    def match_columns(self, std_cols, man_cols, std_name_col, man_name_col):
        std_cols = [c for c in std_cols if str(c).strip() != ""]
        man_cols = list(man_cols)

        mapping = {}
        for std_col in std_cols:
            if std_col == std_name_col:
                continue
            best_match = None
            best_score = 0
            std_key = self.canonicalize(str(std_col))
            for man_col in man_cols:
                if man_col == man_name_col:
                    continue
                man_key = self.canonicalize(str(man_col))
                score = self.match_score(std_key, man_key, str(std_col), str(man_col))
                if score > best_score:
                    best_score = score
                    best_match = man_col
            if best_score >= 0.6:
                mapping[std_col] = best_match
        return mapping

    def similarity(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    def canonicalize(self, text):
        raw = str(text).strip().lower()
        raw = raw.replace(" ", "").replace("_", "").replace("-", "")
        alias_map = {
            "产品名称": "name",
            "产品名": "name",
            "品名": "name",
            "商品名称": "name",
            "商品名": "name",
            "productname": "name",
            "name": "name",
            "型号": "model",
            "规格": "spec",
            "参数": "spec",
            "品牌": "brand",
            "单价": "price",
            "价格": "price",
            "售价": "price",
            "成本": "cost",
            "数量": "qty",
            "件数": "qty",
            "库存": "stock",
            "单位": "unit",
            "产地": "origin",
            "日期": "date",
            "时间": "date",
            "备注": "remark",
            "说明": "remark",
        }
        if raw in alias_map:
            return alias_map[raw]
        return raw

    def match_score(self, std_key, man_key, std_raw, man_raw):
        if std_key == man_key:
            return 1.0
        return max(
            self.similarity(std_key, man_key),
            self.similarity(std_raw, man_raw),
        )

    def values_match(self, std_val, man_val):
        if std_val == man_val:
            return True

        # 尝试数值比较，忽略末尾多余的零
        try:
            if float(std_val) == float(man_val):
                return True
        except (ValueError, TypeError):
            pass

        std_code = self.extract_non_chinese_code(std_val)
        man_code = self.extract_non_chinese_code(man_val)
        return bool(std_code) and std_code == man_code

    def extract_non_chinese_code(self, text):
        normalized = unicodedata.normalize("NFKC", str(text)).strip().lower()
        normalized = re.sub(r"[\u4e00-\u9fff\s]", "", normalized)
        return normalized

    def normalize_product_key(self, name):
        text = unicodedata.normalize("NFKC", str(name)).strip().lower()
        if not text:
            return ""

        parts = text.split()
        key = parts[0] if parts else text
        if len(parts) > 1 and re.fullmatch(r"[a-z]{1,3}", parts[1]):
            key = f"{key}-{parts[1]}"

        m = re.match(r"^[^\u4e00-\u9fff\s]+", key)
        if m:
            return m.group(0).strip().lower()
        return key
