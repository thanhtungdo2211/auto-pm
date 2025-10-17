import json
import os
from typing import Union
import PyPDF2
import docx
import pandas as pd  # 🧩 Thêm pandas để đọc CSV & Excel

def read_file_content(file_path: str) -> Union[str, dict]:
    """
    Đọc nội dung từ file (hỗ trợ .txt, .json, .docx, .pdf, .csv, .xlsx)

    Args:
        file_path (str): Đường dẫn tới file.

    Returns:
        str hoặc dict: Nội dung file hoặc thông báo lỗi.
    """
    try:
        if not os.path.exists(file_path):
            return f"[ERROR] File không tồn tại: {file_path}"

        ext = os.path.splitext(file_path)[1].lower()

        # JSON
        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)

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

        # CSV
        elif ext == ".csv":
            df = pd.read_csv(file_path)
            # Trả về JSON string dễ đọc
            return df.to_json(orient="records", force_ascii=False, indent=2)

        # XLSX
        elif ext == ".xlsx":
            df = pd.read_excel(file_path)
            return df.to_json(orient="records", force_ascii=False, indent=2)

        # TXT hoặc định dạng khác
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

    except Exception as e:
        return f"[ERROR] Không thể đọc file: {str(e)}"