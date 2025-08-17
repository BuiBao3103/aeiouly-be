import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader
from src.config import settings


class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL

        # Setup Jinja2 template environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render HTML template with context"""
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_token: str,
        reset_url: str
    ) -> bool:
        """Send password reset email with beautiful template"""
        try:
            subject = "Đặt lại mật khẩu - Aeiouly"

            # Prepare context for template
            context = {
                "username": username,
                "reset_url": f"{reset_url}?token={reset_token}",
                "token": reset_token,
                "expire_minutes": 30,
                "app_name": "Aeiouly",
                "support_email": "support@aeiouly.com"
            }

            # Render HTML template
            html_content = self._render_template(
                "password_reset.html", context)

            return await self._send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content
            )

        except Exception as e:
            print(
                f"Error sending password reset email: {type(e).__name__}: {e}")
            return False

    async def send_welcome_email(self, to_email: str, username: str) -> bool:
        """Send welcome email with beautiful template"""
        try:
            subject = "Chào mừng bạn đến với Aeiouly!"

            # Prepare context for template
            context = {
                "username": username,
                "app_name": "Aeiouly",
                "login_url": "https://aeiouly.com/login",
                "support_email": "support@aeiouly.com"
            }

            # Render HTML template
            html_content = self._render_template("welcome.html", context)

            return await self._send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content
            )

        except Exception as e:
            print(f"Error sending welcome email: {type(e).__name__}: {e}")
            return False

    async def send_verification_email(
        self,
        to_email: str,
        username: str,
        verification_token: str,
        verification_url: str
    ) -> bool:
        """Send email verification with beautiful template"""
        try:
            subject = "Xác thực email - Aeiouly"

            # Prepare context for template
            context = {
                "username": username,
                "verification_url": f"{verification_url}?token={verification_token}",
                "token": verification_token,
                "app_name": "Aeiouly",
                "support_email": "support@aeiouly.com"
            }

            # Render HTML template
            html_content = self._render_template(
                "email_verification.html", context)

            return await self._send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content
            )

        except Exception as e:
            print(f"Error sending verification email: {type(e).__name__}: {e}")
            return False

    async def send_notification_email(
        self,
        to_email: str,
        username: str,
        notification_type: str,
        message: str,
        action_url: Optional[str] = None
    ) -> bool:
        """Send general notification email"""
        try:
            subject = f"Thông báo - {notification_type} - Aeiouly"

            # Prepare context for template
            context = {
                "username": username,
                "notification_type": notification_type,
                "message": message,
                "action_url": action_url,
                "app_name": "Aeiouly",
                "support_email": "support@aeiouly.com"
            }

            # Render HTML template
            html_content = self._render_template("notification.html", context)

            return await self._send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content
            )

        except Exception as e:
            print(f"Error sending notification email: {type(e).__name__}: {e}")
            return False

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str
    ) -> bool:
        """Send email using SMTP (no TLS/SSL)"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            # Attach HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            print(f"[EmailService] Connecting SMTP {self.smtp_server}:{self.smtp_port} as {self.smtp_username}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            print("[EmailService] Email sent OK")

            return True

        except Exception as e:
            print(f"Error sending email: {type(e).__name__}: {e}")
            return False
