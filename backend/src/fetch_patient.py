import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from fhirclient import client
from fhirclient.models.patient import Patient
from config import CLIENT_ID, TOKEN_URL, PRIVATE_KEY_PATH, FHIR_API_BASE
from auth import EpicAuthClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

auth = EpicAuthClient(CLIENT_ID, TOKEN_URL, PRIVATE_KEY_PATH)
smart = client.FHIRClient({'app_id': CLIENT_ID, 'api_base': FHIR_API_BASE})

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def get_patient(pid):
    token = auth.get_token()
    smart.server.session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept":        "application/fhir+json"
    })
    p = Patient.read(pid, smart.server)
    if not p:
        raise Exception("Empty response")
    return p

if __name__ == "__main__":
    pid = "e63wRTbPfr1p8UW81d8Seiw3"  # replace with a real one
    try:
        pat = get_patient(pid)
        name = pat.name[0]
        logging.info(f"✅ {name.given} {name.family}")
    except Exception as e:
        logging.error(f"❌ Failed: {e}")
