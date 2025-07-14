from dotenv import load_dotenv
import os

load_dotenv(override=True)

CLIENT_ID        = os.getenv("CLIENT_ID")
TOKEN_URL        = os.getenv("TOKEN_URL")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
FHIR_API_BASE    = os.getenv("FHIR_API_BASE")