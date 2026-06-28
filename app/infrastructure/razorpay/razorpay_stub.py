from app.infrastructure.razorpay.razorpay_interface import RazorpayService

class RazorpayStub(RazorpayService):
    async def process_webhook(self, payload: dict, signature: str) -> bool:
        return True
