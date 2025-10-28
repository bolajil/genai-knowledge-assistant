import json
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from utils.enhanced_llm_integration import EnhancedLLMProcessor
except Exception:
    EnhancedLLMProcessor = None  # type: ignore


class ExcelAIAssistant:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self.llm = EnhancedLLMProcessor(model_name=model_name) if EnhancedLLMProcessor else None

    def _call_llm(self, prompt: str) -> str:
        if self.llm:
            try:
                return self.llm._get_llm_response(prompt, model_name=self.model_name)  # type: ignore[attr-defined]
            except Exception:
                return ""
        return ""

    def profile_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        profile: Dict[str, Any] = {}
        profile["shape"] = {"rows": int(len(df)), "cols": int(len(df.columns))}
        try:
            profile["memory_kb"] = float(df.memory_usage(deep=True).sum() / 1024.0)
        except Exception:
            profile["memory_kb"] = None

        cols: List[Dict[str, Any]] = []
        for col in df.columns:
            col_info: Dict[str, Any] = {"name": str(col)}
            s = df[col]
            col_info["dtype"] = str(s.dtype)
            try:
                col_info["non_null"] = int(s.count())
                col_info["nulls"] = int(s.isna().sum())
            except Exception:
                col_info["non_null"] = None
                col_info["nulls"] = None
            try:
                col_info["unique"] = int(s.nunique(dropna=True))
            except Exception:
                col_info["unique"] = None
            try:
                sample_vals = s.dropna().astype(str).head(5).tolist()
                col_info["sample"] = sample_vals
            except Exception:
                col_info["sample"] = []

            if pd.api.types.is_numeric_dtype(s):
                try:
                    d = s.dropna()
                    col_info["stats"] = {
                        "mean": float(d.mean()) if len(d) else None,
                        "std": float(d.std()) if len(d) else None,
                        "min": float(d.min()) if len(d) else None,
                        "max": float(d.max()) if len(d) else None,
                    }
                except Exception:
                    col_info["stats"] = {}
            else:
                try:
                    vc = s.astype(str).value_counts().head(5)
                    col_info["top_values"] = [{"value": str(k), "count": int(v)} for k, v in vc.items()]
                except Exception:
                    col_info["top_values"] = []

            cols.append(col_info)
        profile["columns"] = cols

        # Correlations
        try:
            num_df = df.select_dtypes(include=[np.number])
            if num_df.shape[1] >= 2:
                corr = num_df.corr(numeric_only=True)
                pairs: List[Tuple[str, str, float]] = []
                for i, a in enumerate(corr.columns):
                    for j, b in enumerate(corr.columns):
                        if j <= i:
                            continue
                        val = corr.loc[a, b]
                        if pd.notna(val):
                            pairs.append((str(a), str(b), float(val)))
                pairs.sort(key=lambda x: abs(x[2]), reverse=True)
                profile["top_correlations"] = [
                    {"a": a, "b": b, "corr": round(v, 4)} for a, b, v in pairs[:8]
                ]
            else:
                profile["top_correlations"] = []
        except Exception:
            profile["top_correlations"] = []

        # Heuristic date/time columns
        try:
            date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
            if not date_cols:
                for c in df.columns:
                    if any(k in str(c).lower() for k in ["date", "time", "timestamp"]):
                        try:
                            parsed = pd.to_datetime(df[c], errors="coerce")
                            if not parsed.isna().all():
                                date_cols.append(str(c))
                        except Exception:
                            pass
            profile["date_columns"] = date_cols
        except Exception:
            profile["date_columns"] = []

        return profile

    def generate_insights(self, df: pd.DataFrame, sheet_name: str) -> str:
        profile = self.profile_dataframe(df)
        prompt = (
            "You are an enterprise data analyst. Given the DATAFRAME PROFILE below, write a concise, professional "
            "analysis with these sections: 1) Executive Summary 2) Key Patterns 3) Anomalies & Data Quality 4) "
            "Recommendations. Use complete sentences. Avoid speculation. Keep it 250-450 words.\n\n"
            f"Sheet: {sheet_name}\n\nDATAFRAME PROFILE (JSON):\n{json.dumps(profile, ensure_ascii=False)}\n"
        )
        return self._call_llm(prompt) or ""

    def nlq_to_code(self, df: pd.DataFrame, question: str) -> str:
        cols = [str(c) for c in df.columns]
        dtypes = {str(c): str(df[c].dtype) for c in df.columns}
        example_rows = df.head(3).astype(str).to_dict(orient="records")
        prompt = (
            "You translate a natural language question about a pandas DataFrame into pandas code.\n"
            "Rules:\n"
            "- The DataFrame is named df. pandas is available as pd, numpy as np.\n"
            "- Do NOT import anything. Do NOT read/write files. Do NOT access network or OS.\n"
            "- Only use df/pd/np operations.\n"
            "- Put the final answer in a variable named result.\n"
            "- Return code only, no explanations, no markdown fences.\n\n"
            f"COLUMNS: {cols}\nDTYPES: {json.dumps(dtypes)}\nSAMPLE ROWS: {json.dumps(example_rows, ensure_ascii=False)}\n\n"
            f"QUESTION: {question}\n"
            "Return only Python code that assigns the answer to variable: result"
        )
        return self._call_llm(prompt).strip()

    def recommend_charts(self, df: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
        profile = self.profile_dataframe(df)
        prompt = (
            "Recommend up to 4 charts for this dataset in strict JSON. Keys: title, chart_type, x, y, group_by, reason.\n"
            "- chart_type must be one of: line, bar, histogram, box, scatter, pie.\n"
            "- Use available columns only. If field not applicable, set it to null.\n"
            "- Output only JSON array, no prose.\n\n"
            f"Sheet: {sheet_name}\nPROFILE: {json.dumps(profile, ensure_ascii=False)}"
        )
        raw = self._call_llm(prompt).strip()
        if not raw:
            return []
        try:
            # Remove any markdown fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-zA-Z]*", "", raw).strip()
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
            data = json.loads(raw)
            if isinstance(data, list):
                out: List[Dict[str, Any]] = []
                for item in data[:4]:
                    if isinstance(item, dict):
                        out.append({
                            "title": item.get("title"),
                            "chart_type": item.get("chart_type"),
                            "x": item.get("x"),
                            "y": item.get("y"),
                            "group_by": item.get("group_by"),
                            "reason": item.get("reason"),
                        })
                return out
        except Exception:
            return []
        return []

    def safe_execute_code(self, code: str, df: pd.DataFrame) -> Any:
        blocked = [
            "import ", "os.", "sys.", "subprocess", "open(", "eval(", "exec(", "__",
            "pickle", "requests.", "socket", "pathlib", "to_csv(", "to_excel(", "to_parquet(",
            "read_csv(", "read_excel(", "read_parquet("
        ]
        lowered = code.lower()
        for tok in blocked:
            if tok in lowered:
                raise Exception("Generated code contains disallowed operations")
        safe_globals: Dict[str, Any] = {
            "df": df,
            "pd": pd,
            "np": np,
            "result": None,
        }
        local_env: Dict[str, Any] = {}
        exec(code, safe_globals, local_env)
        return local_env.get("result", safe_globals.get("result"))
