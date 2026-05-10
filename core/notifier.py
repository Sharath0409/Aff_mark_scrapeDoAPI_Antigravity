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
        recipient = "support.remoteprostor@gmail.com"
        logger.info(f"Sending warning email to {recipient}. Remaining topics: {remaining_count}")
        if not self.smtp_email or not self.smtp_password:
            return
            
        msg = MIMEText(f"ALERT: Autoblogger is running out of topics. Only {remaining_count} left.")
        msg['Subject'] = 'Autoblogger Alert: Low Topics'
        msg['From'] = self.smtp_email
        msg['To'] = recipient
        
        try:
            server = smtplib.SMTP(self.host, self.port)
            server.starttls()
            server.login(self.smtp_email, self.smtp_password)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            logger.error(f"Failed to send warning email: {e}")

    def send_report(self, status, topic, details=""):
        """Send a general execution report (success or failure)."""
        recipient = "support.remoteprostor@gmail.com"
        subject = f"Autoblogger {'SUCCESS' if status == 'Success' else 'FATAL FAILURE'}: {topic}"
        body = f"Status: {status}\nTopic: {topic}\n\nDetails:\n{details}"
        
        logger.info(f"Sending report email to {recipient} with status {status}")
        
        if not self.smtp_email or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Skipping email.")
            return
            
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.smtp_email
        msg['To'] = recipient
        
        try:
            server = smtplib.SMTP(self.host, self.port)
            server.starttls()
            server.login(self.smtp_email, self.smtp_password)
            server.send_message(msg)
            server.quit()
            logger.info(f"Report email sent successfully to {recipient}")
        except Exception as e:
            logger.error(f"Failed to send report email: {e}")
