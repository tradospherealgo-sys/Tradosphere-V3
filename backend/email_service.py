"""
Email Service - Send notifications via SendGrid or SMTP
Phase 2: Email alerts for signals, subscription updates, and notifications
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


class EmailService:
    """Email notification service"""

    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str, text_content: str = None):
        """Send email via SMTP or SendGrid"""
        try:
            # Try SendGrid first if API key exists
            sendgrid_api = os.getenv("SENDGRID_API_KEY")
            if sendgrid_api:
                return EmailService._send_via_sendgrid(sendgrid_api, to_email, subject, html_content)

            # Fallback to SMTP
            return EmailService._send_via_smtp(to_email, subject, html_content, text_content)

        except Exception as e:
            print(f"❌ Email send failed: {e}")
            return False

    @staticmethod
    def _send_via_sendgrid(api_key: str, to_email: str, subject: str, html_content: str):
        """Send via SendGrid API"""
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "personalizations": [{
                    "to": [{"email": to_email}],
                    "subject": subject
                }],
                "from": {
                    "email": os.getenv("FROM_EMAIL", "noreply@tradosphere.ai"),
                    "name": "Tradosphere"
                },
                "content": [{
                    "type": "text/html",
                    "value": html_content
                }]
            }
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers,
                timeout=10
            )
            return response.status_code in [200, 202]
        except Exception as e:
            print(f"SendGrid error: {e}")
            return False

    @staticmethod
    def _send_via_smtp(to_email: str, subject: str, html_content: str, text_content: str = None):
        """Send via SMTP (Gmail, etc.)"""
        try:
            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", 587))
            sender_email = os.getenv("SENDER_EMAIL")
            sender_password = os.getenv("SENDER_PASSWORD")

            if not sender_email or not sender_password:
                print("⚠️  SMTP credentials not configured")
                return False

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = sender_email
            message["To"] = to_email

            if text_content:
                message.attach(MIMEText(text_content, "plain"))
            message.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, to_email, message.as_string())

            return True

        except Exception as e:
            print(f"SMTP error: {e}")
            return False


class NotificationTemplates:
    """Email notification templates"""

    @staticmethod
    def welcome_email(first_name: str, email: str):
        """Welcome email for new user"""
        return {
            "subject": "🎉 Welcome to Tradosphere!",
            "html": f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>Welcome to Tradosphere, {first_name}!</h2>
                    <p>We're excited to have you on board. Your account has been successfully created.</p>

                    <h3>Get Started:</h3>
                    <ul>
                        <li><strong>Connect Your Broker</strong> → Settings → API Keys</li>
                        <li><strong>View Live Prices</strong> → Dashboard → Market Data</li>
                        <li><strong>Generate Signals</strong> → Dashboard → Signal Engine</li>
                        <li><strong>Track Performance</strong> → Analytics → Performance Metrics</li>
                    </ul>

                    <p><strong>Your Plan:</strong> Free Tier (100 signals/month, 1 broker)</p>
                    <p>Ready to upgrade? <a href="https://tradosphere.ai/pricing">View Pro & Enterprise plans</a></p>

                    <p>Need help? Email support@tradosphere.ai</p>
                    <hr>
                    <p style="color: #999; font-size: 12px;">© 2026 Tradosphere. All rights reserved.</p>
                </body>
            </html>
            """
        }

    @staticmethod
    def signal_alert_email(first_name: str, signal_type: str, symbol: str, price: float):
        """Signal generation notification"""
        return {
            "subject": f"🎯 New {signal_type} Signal: {symbol}",
            "html": f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>New Trading Signal Generated</h2>
                    <p>Hi {first_name},</p>

                    <div style="background: #f0f0f0; padding: 15px; border-radius: 5px;">
                        <p><strong>Signal Type:</strong> {signal_type}</p>
                        <p><strong>Symbol:</strong> {symbol}</p>
                        <p><strong>Entry Price:</strong> ₹{price}</p>
                        <p><strong>Timestamp:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} IST</p>
                    </div>

                    <p><a href="https://tradosphere.ai/dashboard/signals" style="background: #6366F1; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View in Dashboard</a></p>

                    <p style="color: #999; font-size: 12px;">Always trade responsibly. Past performance doesn't guarantee future results.</p>
                </body>
            </html>
            """
        }

    @staticmethod
    def subscription_confirmation_email(first_name: str, plan_tier: str, price: float, next_billing: str):
        """Subscription confirmation"""
        return {
            "subject": f"✅ Subscription Confirmed - {plan_tier.title()} Plan",
            "html": f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>Subscription Confirmed</h2>
                    <p>Hi {first_name},</p>

                    <p>Your subscription to Tradosphere {plan_tier.title()} has been confirmed.</p>

                    <div style="background: #f0f0f0; padding: 15px; border-radius: 5px;">
                        <p><strong>Plan:</strong> {plan_tier.title()}</p>
                        <p><strong>Monthly Price:</strong> ₹{price}</p>
                        <p><strong>Next Billing Date:</strong> {next_billing}</p>
                        <p><strong>Status:</strong> Active</p>
                    </div>

                    <h3>Your {plan_tier.title()} Plan Includes:</h3>
                    <ul>
                        <li>Live market prices & technical analysis</li>
                        <li>Signal generation & alerts</li>
                        <li>Advanced analytics & performance tracking</li>
                        <li>Priority email support</li>
                        <li>Multiple broker support</li>
                    </ul>

                    <p><a href="https://tradosphere.ai/dashboard" style="background: #6366F1; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Dashboard</a></p>

                    <p>Questions? Contact support@tradosphere.ai</p>
                </body>
            </html>
            """
        }

    @staticmethod
    def usage_alert_email(first_name: str, used: int, limit: int, resource_type: str):
        """Usage limit warning"""
        percentage = int((used / limit) * 100)
        return {
            "subject": f"⚠️ Usage Alert: {percentage}% of {resource_type} used",
            "html": f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>Usage Alert</h2>
                    <p>Hi {first_name},</p>

                    <p>You've used <strong>{percentage}%</strong> of your monthly {resource_type} limit.</p>

                    <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                        <p><strong>{resource_type}:</strong> {used}/{limit}</p>
                        <p>Remaining: {limit - used}</p>
                    </div>

                    <p>Upgrade to a higher plan to increase limits and unlock more features.</p>
                    <p><a href="https://tradosphere.ai/pricing" style="background: #6366F1; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Upgrade Now</a></p>
                </body>
            </html>
            """
        }

    @staticmethod
    def broker_connection_alert(first_name: str, broker: str, status: str):
        """Broker connection status"""
        color = "green" if status == "connected" else "red"
        icon = "✅" if status == "connected" else "❌"
        return {
            "subject": f"{icon} {broker} Connection {status.title()}",
            "html": f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>{broker} Broker Status</h2>
                    <p>Hi {first_name},</p>

                    <div style="background: #f0f0f0; padding: 15px; border-radius: 5px; border-left: 4px solid {color};">
                        <p><strong>Broker:</strong> {broker}</p>
                        <p><strong>Status:</strong> <span style="color: {color}; font-weight: bold;">{status.upper()}</span></p>
                        <p><strong>Timestamp:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} IST</p>
                    </div>

                    {f'<p>Please check your API credentials in Settings → API Keys</p>' if status == 'disconnected' else '<p>Your broker connection is active. You can start trading!</p>'}

                    <p><a href="https://tradosphere.ai/settings/api-keys" style="background: #6366F1; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Manage API Keys</a></p>
                </body>
            </html>
            """
        }

    @staticmethod
    def monthly_report_email(first_name: str, stats: dict):
        """Monthly performance report"""
        return {
            "subject": "📊 Your Tradosphere Monthly Report",
            "html": f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>Your Monthly Report</h2>
                    <p>Hi {first_name},</p>

                    <p>Here's your Tradosphere performance summary for {datetime.utcnow().strftime('%B %Y')}:</p>

                    <div style="background: #f0f0f0; padding: 15px; border-radius: 5px;">
                        <p><strong>Signals Generated:</strong> {stats.get('signals', 0)}</p>
                        <p><strong>Trades Executed:</strong> {stats.get('trades', 0)}</p>
                        <p><strong>Winning Trades:</strong> {stats.get('wins', 0)}</p>
                        <p><strong>Win Rate:</strong> {stats.get('win_rate', 0):.1f}%</p>
                        <p><strong>Total P&L:</strong> ₹{stats.get('pnl', 0):.2f}</p>
                    </div>

                    <p><a href="https://tradosphere.ai/dashboard/analytics" style="background: #6366F1; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Full Analytics</a></p>

                    <p>Keep trading responsibly!</p>
                </body>
            </html>
            """
        }


# ===== NOTIFICATION SENDER =====
class NotificationSender:
    """Send notifications to users"""

    @staticmethod
    def send_welcome(user_email: str, first_name: str):
        """Send welcome email"""
        template = NotificationTemplates.welcome_email(first_name, user_email)
        return EmailService.send_email(user_email, template["subject"], template["html"])

    @staticmethod
    def send_signal_alert(user_email: str, first_name: str, signal: dict):
        """Send signal generation alert"""
        template = NotificationTemplates.signal_alert_email(
            first_name,
            signal.get("type", "BUY"),
            signal.get("symbol", "NIFTY"),
            signal.get("price", 0)
        )
        return EmailService.send_email(user_email, template["subject"], template["html"])

    @staticmethod
    def send_subscription_confirmation(user_email: str, first_name: str, plan_tier: str, price: float, next_billing: str):
        """Send subscription confirmation"""
        template = NotificationTemplates.subscription_confirmation_email(first_name, plan_tier, price, next_billing)
        return EmailService.send_email(user_email, template["subject"], template["html"])

    @staticmethod
    def send_usage_alert(user_email: str, first_name: str, used: int, limit: int, resource: str):
        """Send usage warning"""
        template = NotificationTemplates.usage_alert_email(first_name, used, limit, resource)
        return EmailService.send_email(user_email, template["subject"], template["html"])

    @staticmethod
    def send_broker_status(user_email: str, first_name: str, broker: str, status: str):
        """Send broker status update"""
        template = NotificationTemplates.broker_connection_alert(first_name, broker, status)
        return EmailService.send_email(user_email, template["subject"], template["html"])

    @staticmethod
    def send_monthly_report(user_email: str, first_name: str, stats: dict):
        """Send monthly report"""
        template = NotificationTemplates.monthly_report_email(first_name, stats)
        return EmailService.send_email(user_email, template["subject"], template["html"])


if __name__ == "__main__":
    print("✅ Email service module ready")
