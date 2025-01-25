from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import zipfile
from pydantic import BaseModel
from pathlib import Path
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


# โหลดค่าตัวแปรจากไฟล์ .env
load_dotenv()

app = FastAPI()

# เปิดใช้งาน CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# กำหนดค่าการเชื่อมต่อ MySQL จากตัวแปร .env
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

DOCUMENTS_FOLDER = Path("./documents")

class SignInRequest(BaseModel):
    username: str
    password: str

def get_db_connection():
    """เชื่อมต่อกับ MySQL database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")
    return None
 
@app.get("/hello")
async def hello():
    return {"message": "Hello, World!"}


@app.get("/api/db-status") 
async def check_db_connection():
    """
    ตรวจสอบสถานะการเชื่อมต่อกับฐานข้อมูล
    
    """
    connection = None
    try:
        connection = get_db_connection()
        if connection and connection.is_connected():
            return {"success": True, "message": "Connected to MySQL database successfully"}
        else:
            return {"success": False, "message": "Unable to connect to the database"}
    except Exception as e:
        return {"success": False, "message": f"Database connection error: {str(e)}"}
    finally:
        if connection and connection.is_connected():
            connection.close()


# @app.post("/api/user/signIn")
# async def sign_in(user: SignInRequest):
#     connection = get_db_connection()
#     try:
#         print(f"Username: {user.username}, Password: {user.password}")
#         cursor = connection.cursor(dictionary=True)
#         query = """
#             SELECT in_numcard, in_name_surname
#             FROM income 
#             WHERE in_numcard = %s AND RIGHT(in_numcard, 4) = %s
#         """
#         cursor.execute(query, (user.username, user.password))
        
#         # ดึงผลลัพธ์ทั้งหมดก่อน
#         user_data = cursor.fetchall()
        
#         if user_data:
#             print(f"Query Result: {user_data}")
#             return {
#                 "token": "mock_token_12345",  # จำลอง Token
#                 "id": user_data[0]["in_numcard"],  # ใช้แถวแรก
#                 "name": user_data[0]["in_name_surname"],  # ใช้แถวแรก
#                 "level": "user"
#             }
#         else:
#             raise HTTPException(status_code=401, detail="Invalid username or password")
#     except Exception as e:
#         print(f"Error querying MySQL: {e}")
#         raise HTTPException(status_code=500, detail="Database query error")
#     finally:
#         if connection.is_connected():
#             cursor.close()  # ปิด cursor
#             connection.close()  # ปิด connection

@app.post("/api/user/signIn")
async def sign_in(user: SignInRequest):
    # ตรวจสอบว่าผู้ใช้คือ admin หรือไม่
    if user.username == "admin" and user.password == "admin":
        return {
            "token": "mock_token_admin",  # จำลอง Token สำหรับ admin
            "id": "admin",  # ค่า id สำหรับ admin
            "name": "Administrator",  # ชื่อสำหรับ admin
            "level": "admin"  # ระดับ admin
        }

    # หากไม่ใช่ admin ให้คิวรีฐานข้อมูล
    connection = get_db_connection()
    try:
        print(f"Username: {user.username}, Password: {user.password}")
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT name, username,level
            FROM users 
            WHERE username = %s AND password = %s
        """
        cursor.execute(query, (user.username, user.password))
        
        user_data = cursor.fetchall()
        
        if user_data:
            print(f"Query Result: {user_data}")
            return {
                "token": "mock_token_12345",  # จำลอง Token
                "id": user_data[0]["username"],  # ใช้แถวแรก
                "name": user_data[0]["name"],  # ใช้แถวแรก
                "level": user_data[0]["level"]  # ระดับ user
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid username or password")
    except Exception as e:
        print(f"Error querying MySQL: {e}")
        raise HTTPException(status_code=500, detail="Database query error")
    finally:
        if connection.is_connected():
            cursor.close()  # ปิด cursor
            connection.close()  # ปิด connection




@app.get("/documents/{national_id}")
async def get_document(national_id: str):
    """
    ดึงไฟล์ PDF ตามหมายเลขบัตรประชาชน
    """
    file_path = DOCUMENTS_FOLDER / f"{national_id}.pdf"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารสำหรับหมายเลขบัตรประชาชนนี้")

    return FileResponse(path=file_path, media_type="application/pdf", filename=f"{national_id}.pdf")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        for existing_file in DOCUMENTS_FOLDER.glob("*"):
            if existing_file.is_file():
                os.remove(existing_file)

        zip_path = f"./uploads/{file.filename}"
        with open(zip_path, "wb") as f:
            f.write(await file.read())

        extracted_files = []
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for zip_file in zip_ref.namelist():
                zip_file_name = os.path.basename(zip_file)
                if not zip_file.endswith('/'):
                    existing_file = DOCUMENTS_FOLDER / zip_file_name
                    if existing_file.exists():
                        os.remove(existing_file)
                    zip_ref.extract(zip_file, DOCUMENTS_FOLDER)
                    os.rename(DOCUMENTS_FOLDER / zip_file, DOCUMENTS_FOLDER / zip_file_name)
                    extracted_files.append(zip_file_name)
        
        os.remove(zip_path)
        pdf_url = f"/documents/{extracted_files[-1]}" if extracted_files else None
        
        return JSONResponse(content={
            "success": True, 
            "pdfUrl": pdf_url,
            "filesUploaded": len(extracted_files),
        })
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)