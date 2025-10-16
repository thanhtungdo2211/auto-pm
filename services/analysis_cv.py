import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import docx
from PyPDF2 import PdfReader
import json

load_dotenv('./.env')
os.environ["OPENAI_API_KEY"] = os.getenv("API_KEY")
# print("Using OpenAI API Key:", "****" + os.environ["OPENAI_API_KEY"][-4:])

class Project(BaseModel):
    name: str
    role: Optional[str]
    contribution: Optional[str]

class Candidate(BaseModel):
    id: str
    name: str
    role: Optional[str]
    email: Optional[str]
    experience_years: Optional[int]
    experience_level: Optional[str]
    skills: Optional[List[str]]
    strengths: Optional[List[str]]
    projects: Optional[List[Project]]
    note: Optional[str] = None

class CVResponse(BaseModel):
    candidates: List[Candidate]

class GenCVAnalyzer:
    def __init__(self):
        self.base_url = os.getenv("BASE_URL", "https://api.openai.com/v1")
        self.model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
        self.llm = init_chat_model(
            model=self.model_name,
            model_provider="openai",
            base_url=self.base_url
        ).with_structured_output(CVResponse)
    def extract_text_from_file(self, file_path: str) -> str:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"❌ File không tồn tại: {file_path}")

        if file_path.suffix.lower() == ".pdf":
            reader = PdfReader(file_path)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif file_path.suffix.lower() == ".docx":
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
        else:
            raise ValueError("❌ Chỉ hỗ trợ file PDF hoặc DOCX.")
        return text.strip()
    def query(self, cv_path: str):
        """
        Phân tích nội dung CV (đã trích xuất text từ PDF/DOCX)
        và trả về thông tin JSON theo cấu trúc 'candidates'.
        """
        cv_text = self.extract_text_from_file(cv_path)
        prompt =  """
            You are an **AI assistant specialized in analyzing candidate resumes (CVs)**.  
            Your task is to read, understand, and extract key information from the provided CV content (already converted into plain text).

            ---

            **Objective**
            - Analyze and understand the context of each candidate’s CV.
            - Extract accurate, structured, and well-organized information.
            - Normalize the data into a standardized JSON format.

            ---

            **Required JSON Output Format:**
            {
            "candidates": [
                {
                "id": "<string>",
                "name": "<string>",
                "role": "<string>",
                "email": "<string>",
                "experience_years": <int>,
                "experience_level": "<string>",
                "skills": ["skill_1", "skill_2", ...],
                "strengths": ["strength_1", "strength_2", ...],
                "projects": [
                    {
                    "name": "<string>",
                    "role": "<string>",
                    "contribution": "<string>"
                    }
                ],
                "note": null
                }
            ]
            }

            ---

            **Detailed Extraction Rules**

            1 **Basic Information**
            - `"name"`: The candidate’s full name. Prioritize names found at the beginning of the CV or in the contact section.  
            - `"email"`: The candidate’s email address, if available.  
            - `"role"`: The job title or position applied for (e.g., “Backend Developer”, “Data Scientist”, etc.).  

            2 **Experience**
            - `"experience_years"`: Total years of professional experience, estimated based on sections like "Work Experience", "Employment", or "Professional Experience".  
            - If no explicit duration is stated, **reasonably infer** the number of years from job descriptions, project timelines, or the earliest mentioned employment year.  
            - `"experience_level"`:
            - Must be inferred using **both** years of experience and the level of skills or responsibilities demonstrated in the CV.  
            - Use contextual judgment (e.g., technical complexity, leadership role, autonomy level).  
            - If uncertain, set to `null`.  

            3 **Skills**
            - `"skills"`: A list of **technical skills**, such as:  
            - Programming languages: Python, Java, C#, JavaScript, etc.  
            - Frameworks/technologies: Django, React, Node.js, TensorFlow, etc.  
            - Databases: MySQL, PostgreSQL, MongoDB, etc.  
            - Tools: Docker, Git, AWS, etc.  
            - Separate technical skills from soft skills. Do not mix both in the `"skills"` field.  

            4 **Strengths / Soft Skills**
            - `"strengths"`: A list of personal strengths, soft skills, or notable traits mentioned in the CV.  
            Examples:  
            - “Strong logical thinking”, “Good teamwork”, “Proactive learner”, “Excellent communication skills”.  

            5 **Projects**
            - `"projects"`: A list of key projects the candidate has participated in.  
            Each project object includes:  
            - `"name"`: Project title or short description.  
            - `"role"`: The candidate’s role in that project (e.g., “Backend Developer”, “Data Engineer”).  
            - `"contribution"`: A short description of the candidate’s contributions or responsibilities.  
            - If multiple projects exist, list them all in the `"projects"` array.  
            - If none are mentioned, return an empty array `[]`.  

            6 **Notes**
            - `"note"`: Always set this field to `null` by default.  

            7 **General Rules**
            - Ensure the output is **valid JSON**, with no extra text outside the structure.  
            - Do **not** include explanations or reasoning in the output.  
            - All string values must be enclosed in double quotes `"..."`.  

            ---

            **Below is the CV content to analyze:**

            """

        response = self.llm.invoke(prompt + "\n" + cv_text)
        return response

# Example usage
# if __name__ == "__main__":
#     cv_path = "/home/mq-dev/tungdt/auto-pm/data/cv_test.pdf"
#     try:
#         bot = GenCVAnalyzer()
#         result = bot.query(cv_path)
#         print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
#     #     Sample output
#     # {
#     #   "candidates": [
#     #     {
#     #       "id": "string",
#     #       "name": "Đỗ Thanh Tùng",
#     #       "role": "AI Engineer",
#     #       "email": "tung.0982548086@gmail.com",
#     #       "experience_years": 2,
#     #       "experience_level": "Junior",
#     #       "skills": [
#     #         "Python",
#     #         "C/C++",
#     #         "PyTorch",
#     #         "TensorFlow",
#     #         "OpenCV",
#     #         "Numpy",
#     #         "YOLOv7",
#     #         "YOLOv5n",
#     #         "YOLOv8n",
#     #         "Docker",
#     #         "StreamLit",
#     #         "PaddleOCR",
#     #         "VietOCR",
#     #         "DB"
#     #       ],
#     #       "strengths": [
#     #         "Strong logical thinking",
#     #         "Proactive learner"
#     #       ],
#     #       "projects": [
#     #         {
#     #           "name": "Drowning Detection",
#     #           "role": "Member",
#     #           "contribution": "Developed a system for detecting drowning using YOLOv7 and Grid Tracker, achieving high accuracy."
#     #         },
#     #         {
#     #           "name": "Invoice Extraction",
#     #           "role": "Member",
#     #           "contribution": "Built an invoice information extraction system using DB for text detection and Transformer OCR for text recognition."
#     #         },
#     #         {
#     #           "name": "Violence Detection",
#     #           "role": "Member",
#     #           "contribution": "Developed a violence detection system using Yolov5n, Yolov7tiny, Yolov8n, and implemented identity verification using CNN."
#     #         }
#     #       ],
#     #       "note": null
#     #     }
#     #   ]
#     # }
#     except Exception as e:
#         print(f"❌ Error: {e}")
