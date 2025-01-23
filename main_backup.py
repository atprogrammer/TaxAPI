from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import zipfile
from pydantic import BaseModel
from pathlib import Path
import os

app = FastAPI()

# เปิดใช้งาน CORS
app.add_middleware(
    CORSMiddleware,
    #allow_origins=["*"],  # กำหนด Origin ของ Frontend
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock Database (ข้อมูลจำลอง)
MOCK_USERS = {
    "admin": {
        "password": "1234",  # รหัสผ่านจำลอง
        "name": "อรรถ",
        "id": 1,
        "nationalId": "1234567890123",  # เลขบัตรประชาชน
        "level": "admin"
    },
    "3100700151137": {
        "password": "1137",
        "name": "ครรชิต เจิมจิตรผ่อง",
        "id": 2,
        "nationalId": "3100700151137",
        "level": "user"
    },
     "3110401491041": {
        "password": "1041",
        "name": "เกื้อกูล เพ็ชรสันทัด",
        "id": 2,
        "nationalId": "3110401491041",
        "level": "user"
    }
}

DOCUMENTS_FOLDER = Path("./documents")

class SignInRequest(BaseModel):
    username: str
    password: str

@app.get("/hello")
async def hello():
    return {"message": "Hello, Worlddd!"}


@app.post("/api/user/signIn")
async def sign_in(user: SignInRequest):
    """
    ตรวจสอบ Username และ Password
    """
    # ตรวจสอบ Username และ Password ใน Mock Database
    user_data = MOCK_USERS.get(user.username)
    if not user_data or user_data["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # ส่งข้อมูลกลับไปยัง Frontend
    return {
        "token": "mock_token_12345",  # จำลอง Token
        "id": user_data["id"],
        "nationalId": user_data["nationalId"],
        "name": user_data["name"],
        "level": user_data["level"]
    }

@app.get("/documents/{national_id}")
async def get_document(national_id: str):
    """
    ดึงไฟล์ PDF ตามหมายเลขบัตรประชาชน
    """
    # ตรวจสอบว่าไฟล์มีอยู่หรือไม่
    file_path = DOCUMENTS_FOLDER / f"{national_id}.pdf"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารสำหรับหมายเลขบัตรประชาชนนี้")

    # ส่งไฟล์ PDF กลับไปยังผู้ใช้งาน
    return FileResponse(path=file_path, media_type="application/pdf", filename=f"{national_id}.pdf")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # การจัดการไฟล์ที่อัพโหลด
    try:
        # ลบไฟล์ทั้งหมดในโฟลเดอร์ documents ก่อนการอัปโหลดไฟล์ใหม่
        for existing_file in DOCUMENTS_FOLDER.glob("*"):
            if existing_file.is_file():  # ตรวจสอบว่าเป็นไฟล์
                os.remove(existing_file)

        # บันทึกไฟล์ ZIP ที่ได้รับ
        zip_path = f"./uploads/{file.filename}"
        with open(zip_path, "wb") as f:
            f.write(await file.read())

        # แยกไฟล์ ZIP โดยตรงไปยังโฟลเดอร์ documents
        extracted_files = []  # สร้างรายชื่อไฟล์ที่แตกออก
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for zip_file in zip_ref.namelist():
                # กำจัดโครงสร้างโฟลเดอร์ออก
                zip_file_name = os.path.basename(zip_file)  # ใช้แค่ชื่อไฟล์
                if not zip_file.endswith('/'):  # ตรวจสอบว่าเป็นไฟล์
                    # ลบไฟล์เก่าหากมี
                    existing_file = DOCUMENTS_FOLDER / zip_file_name
                    if existing_file.exists():
                        os.remove(existing_file)  # ลบไฟล์เก่าทิ้ง
                    
                    # แตกไฟล์ไปยัง /documents โดยไม่สร้างโฟลเดอร์
                    zip_ref.extract(zip_file, DOCUMENTS_FOLDER)
                    os.rename(DOCUMENTS_FOLDER / zip_file, DOCUMENTS_FOLDER / zip_file_name)  # เปลี่ยนชื่อไฟล์เป็นชื่อไฟล์ที่ไม่มีโฟลเดอร์
                    extracted_files.append(zip_file_name)  # เพิ่มชื่อไฟล์ที่แตกออกในรายการ
        
        # ลบไฟล์ ZIP หลังจากที่แตกเสร็จแล้ว
        os.remove(zip_path)

        # สร้าง URL สำหรับไฟล์ PDF ที่ถูกแยกออกมา
        pdf_url = f"/documents/{extracted_files[-1]}" if extracted_files else None
        
        return JSONResponse(content={
            "success": True, 
            "pdfUrl": pdf_url,
            "filesUploaded": len(extracted_files),  # ส่งคืนจำนวนไฟล์ที่ถูกอัปโหลด
        })
    
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
