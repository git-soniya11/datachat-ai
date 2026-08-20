from fastapi import APIRouter, HTTPException, status
import pandasai as pai
from pandasai_litellm.litellm import LiteLLM
from pathlib import Path
from dotenv import load_dotenv
import os
from pydantic import BaseModel


# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------

load_dotenv()

apikey = os.environ.get("APIKEY")
model = os.environ.get("MODEL")


# ---------------------------------------------------------
# UPLOAD DIRECTORY
# ---------------------------------------------------------

upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)


# ---------------------------------------------------------
# LLM CONFIGURATION
# ---------------------------------------------------------

llm = LiteLLM(
    model=model,
    api_key=apikey
)

# Configure PandasAI to use this LLM
pai.config.set({
    "llm": llm
})


# ---------------------------------------------------------
# ROUTER
# ---------------------------------------------------------

router = APIRouter(
    tags=["Chat Service"]
)


# ---------------------------------------------------------
# REQUEST MODEL
# ---------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    files: list[str]


# ---------------------------------------------------------
# CHAT ENDPOINT
# ---------------------------------------------------------

@router.post("/chat")
def chat_with_files(request: ChatRequest):

    try:

        dataframes = []

        # -------------------------------------------------
        # LOAD ALL REQUESTED FILES
        # -------------------------------------------------

        for filename in request.files:

            file_path = upload_dir / filename

            if not file_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found: {filename}"
                )

            extension = file_path.suffix.lower()

            if extension == ".csv":

                df = pai.read_csv(file_path)

            elif extension == ".xlsx":

                df = pai.read_excel(file_path)

            else:

                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {extension}"
                )

            dataframes.append(df)

        # -------------------------------------------------
        # CHAT WITH DATA
        # -------------------------------------------------

        if len(dataframes) == 1:

            response = pai.chat(
                request.message,
                dataframes[0]
            )

        else:

            response = pai.chat(
                request.message,
                dataframes
            )

        # -------------------------------------------------
        # HANDLE PANDASAI RESPONSE
        # -------------------------------------------------

        if hasattr(response, "type") and hasattr(response, "value"):

            response_value = response.value

            # DataFrame response
            if hasattr(response_value, "astype"):

                response_value = response_value.astype(str)

                return {
                    "type": response.type,
                    "value": response_value.to_dict(
                        orient="records"
                    )
                }

            # Normal response
            return {
                "type": response.type,
                "value": response_value
            }

        # -------------------------------------------------
        # FALLBACK RESPONSE
        # -------------------------------------------------

        return {
            "type": "text",
            "value": str(response)
        }

    # -----------------------------------------------------
    # HTTP EXCEPTIONS
    # -----------------------------------------------------

    except HTTPException:
        raise

    # -----------------------------------------------------
    # OTHER EXCEPTIONS
    # -----------------------------------------------------

    except Exception as e:

        print("CHAT ERROR:", repr(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )