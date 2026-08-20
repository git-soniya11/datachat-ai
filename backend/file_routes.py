
from fastapi import APIRouter, UploadFile, HTTPException, File, status
from pathlib import Path
import os
import pandas as pd

# router = APIRouter()
router = APIRouter(
    tags=["File Service"]
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/uploads")
async def upload_file(file: UploadFile = File(...)):

    try:
        allowed_extensions = [".csv", ".xlsx"]

        file_extension = Path(file.filename).suffix.lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV and XLSX files are allowed"
            )

        content = await file.read()

        file_path = UPLOAD_DIR / file.filename

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        return {
            "message": "File uploaded successfully",
            "filename": file.filename
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/files")
def list_uploaded_files():
    try:
        files = []

        for file in UPLOAD_DIR.iterdir():
            files.append({
                "filename": file.name
            })

        return {
            "total_files": len(files),
            "files": files
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )
    

@router.delete("/files/{filename}")
def delete_file(filename: str):
    try:
        file_path = UPLOAD_DIR / filename

        os.remove(file_path)

        return filename + " - File deleted"

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        ) 

@router.get("/files/{filename}/preview")
def preview_file(filename: str):
    try:
        file_path = UPLOAD_DIR / filename

        extension = file_path.suffix.lower()

        if extension == ".csv":
            df = pd.read_csv(file_path)

        elif extension == ".xlsx":
            df = pd.read_excel(file_path)

        df = df.astype(str)    

        return {
            "filename": filename,
            "preview": df.to_dict(orient="records")
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )
