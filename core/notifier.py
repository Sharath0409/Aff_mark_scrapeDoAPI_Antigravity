import smtplib
from email.mime.text import MIMEText
from config.logger import get_logger
from config import settings

logger = get_logger(__name__)

class EmailNotifier:
    def __init__(self):
        self.smtp_email = settings.SMTP_EMAIL
        self.smtp_password = settings.SMTP_APP_PASSWORD
        self.host = "smtp.gmail.com"
        self.port = 587
        
    def send_warning(self, remaining_count):
        """Send email when topics are low."""
        logger.info(f"Sending warning email. Remaining topics: {remaining_count}")
        if not self.smtp_email or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Skipping email.")
            return
            
        msg = MIMEText(f"ALERT: Autoblogger is running out of topics. Only {remaining_count} left. Please update the Google Sheet.")
        msg['Subject'] = 'Autoblogger Alert: Low Topics'
        msg['From'] = self.smtp_email
        msg['To'] = self.smtp_email
        
        try:
            # server = smtplib.SMTP(self.host, self.port)
            # server.starttls()
            # server.login(self.smtp_email, self.smtp_password)
            # server.send_message(msg)
            # server.quit()
            logger.info("Mock email sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
