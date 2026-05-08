# pyrefly: ignore [missing-import]
from tenacity import retry, stop_after_attempt, wait_exponential

def get_retry_decorator():
    return retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
