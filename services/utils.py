import json
import os
from typing import Union
import PyPDF2
import docx
import pandas as pd
import math

def remove_nulls(obj):
    """Đệ quy xóa tất cả key có giá trị null / NaN / None / '' trong dict hoặc list"""
    if isinstance(obj, dict):
        return {
            k: remove_nulls(v)
            for k, v in obj.items()
            if v not in [None, "", "null"] and not (isinstance(v, float) and math.isnan(v))
        }
    elif isinstance(obj, list):
        return [remove_nulls(v) for v in obj if v not in [None, "", "null"] and not (isinstance(v, float) and math.isnan(v))]
    else:
        return obj


def read_file_content(file_path: str) -> str:
    """
    Đọc nội dung từ file (.txt, .json, .docx, .pdf, .csv, .xlsx)
    - Tự động xử lý lỗi encoding
    - Loại bỏ cột/hàng trống trong CSV và Excel
    - Sau khi chuyển sang JSON, xóa tất cả các giá trị null / NaN / None / ''
    - **LUÔN TRẢ VỀ STRING** để gửi qua API (escaped JSON string cho CSV/Excel/JSON)
    """
    try:
        if not os.path.exists(file_path):
            return f"[ERROR] File không tồn tại: {file_path}"

        ext = os.path.splitext(file_path)[1].lower()

        # JSON - Convert to escaped JSON string
        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cleaned_data = remove_nulls(data)
                # Return as compact JSON string (no indent for API)
                return json.dumps(cleaned_data, ensure_ascii=False)

        # DOCX
        elif ext == ".docx":
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])

        # PDF
        elif ext == ".pdf":
            text = ""
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()

        # CSV - Convert to escaped JSON string (compact format)
        elif ext == ".csv":
            encodings_to_try = ["utf-8", "utf-8-sig", "latin1", "cp1252", "utf-16"]
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
                    data = json.loads(df.to_json(orient="records", force_ascii=False))
                    cleaned_data = remove_nulls(data)
                    # Return as compact JSON string (no indent, no spaces)
                    return json.dumps(cleaned_data, ensure_ascii=False, separators=(',', ':'))
                except Exception:
                    continue
            return f"[ERROR] Không thể đọc file CSV với các encoding thông dụng: {encodings_to_try}"

        # XLSX - Convert to escaped JSON string (compact format)
        elif ext == ".xlsx":
            try:
                df = pd.read_excel(file_path)
                df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
                data = json.loads(df.to_json(orient="records", force_ascii=False))
                cleaned_data = remove_nulls(data)
                # Return as compact JSON string (no indent, no spaces)
                return json.dumps(cleaned_data, ensure_ascii=False, separators=(',', ':'))
            except Exception as e:
                return f"[ERROR] Không thể đọc file Excel: {str(e)}"

        # TXT hoặc định dạng khác
        else:
            encodings_to_try = ["utf-8", "utf-8-sig", "latin1", "cp1252", "utf-16"]
            for enc in encodings_to_try:
                try:
                    with open(file_path, "r", encoding=enc) as f:
                        return f.read()
                except Exception:
                    continue
            return f"[ERROR] Không thể đọc file text với các encoding thông dụng: {encodings_to_try}"

    except Exception as e:
        return f"[ERROR] Không thể đọc file: {str(e)}"


# Test
if __name__ == "__main__":
    test_file = "/home/mq-dev/tungdt/auto-pm/data/WBS_AI_Team_MQ_final(ProjectSchedule_FaceSpa).csv"
    content = read_file_content(test_file)
    print(content)
    # print(f"Type: {type(content)}")  # Should be <class 'str'>
    # print(f"Length: {len(content)}")
    # print(f"First 500 chars:\n{content[:500]}")
    
    # # Test JSON payload
    # import httpx
    # payload = {
    #     "user_id": 123,
    #     "query": "",
    #     "file": content  # This will be auto-escaped by json.dumps
    # }
    # print("\n=== JSON Payload ===")
    # print(json.dumps(payload, ensure_ascii=False, indent=2)[:1000])