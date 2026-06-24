"""
Email Templates - Production HTML email templates
"""

EMAIL_TEMPLATES = {
    'welcome': {
        'subject': 'Welcome to Tradosphere - Start Your Paper Trading Journey',
        'html': '''
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #667eea; margin: 0; }
        .content { color: #333; line-height: 1.6; }
        .button { display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .footer { text-align: center; color: #999; font-size: 12px; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Welcome to Tradosphere</h1>
        </div>
        <div class="content">
            <p>Hi {{name}},</p>
            <p>Thank you for signing up for Tradosphere - the ultimate paper trading platform!</p>
            <p>Your account is ready to use. You can now:</p>
            <ul>
                <li>Get real-time trading signals</li>
                <li>Paper trade with ₹100,000 virtual capital</li>
                <li>View live market data and charts</li>
                <li>Track your portfolio performance</li>
                <li>Backtest your strategies</li>
            </ul>
            <p>
                <a href="https://tradosphere.com/dashboard" class="button">Go to Dashboard</a>
            </p>
            <p>Happy trading!</p>
            <p>Best regards,<br>Tradosphere Team</p>
        </div>
        <div class="footer">
            <p>© 2026 Tradosphere. All rights reserved.</p>
            <p>This is a paper trading platform. No real money trading.</p>
        </div>
    </div>
</body>
</html>
        '''
    },
    'verification': {
        'subject': 'Verify Your Email - Tradosphere',
        'html': '''
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; }
        .code { text-align: center; background: #f9fafb; padding: 20px; border-radius: 6px; font-size: 24px; font-weight: bold; color: #667eea; letter-spacing: 4px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Verify Your Email</h1>
        <p>Hi {{name}},</p>
        <p>Your verification code is:</p>
        <div class="code">{{code}}</div>
        <p>This code expires in 24 hours.</p>
        <p>If you didn't request this, please ignore this email.</p>
    </div>
</body>
</html>
        '''
    },
    'password_reset': {
        'subject': 'Reset Your Password - Tradosphere',
        'html': '''
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; }
        .button { display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Reset Your Password</h1>
        <p>Hi {{name}},</p>
        <p>Click the button below to reset your password:</p>
        <p>
            <a href="{{reset_link}}" class="button">Reset Password</a>
        </p>
        <p>This link expires in 24 hours.</p>
        <p>If you didn't request this, please ignore this email.</p>
    </div>
</body>
</html>
        '''
    },
    'subscription': {
        'subject': 'Subscription Confirmation - Tradosphere',
        'html': '''
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; }
        .plan-info { background: #f9fafb; padding: 20px; border-radius: 6px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Subscription Confirmed</h1>
        <p>Hi {{name}},</p>
        <p>Your subscription has been activated!</p>
        <div class="plan-info">
            <h3>Plan: {{plan}}</h3>
            <p>Amount: {{amount}}</p>
            <p>Billing Cycle: {{cycle}}</p>
            <p>Renewal Date: {{renewal_date}}</p>
        </div>
        <p>You now have access to all {{plan}} features.</p>
        <p>Thank you for subscribing!</p>
    </div>
</body>
</html>
        '''
    },
    'signal_alert': {
        'subject': 'New Trading Signal - {{symbol}} - Tradosphere',
        'html': '''
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; }
        .signal-box { background: #f9fafb; padding: 20px; border-radius: 6px; margin: 20px 0; border-left: 4px solid {{color}}; }
        .bullish { color: #10b981; }
        .bearish { color: #ef4444; }
        .button { display: inline-block; background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="{{direction}}">{{direction|upper}} Signal - {{symbol}}</h1>
        <div class="signal-box">
            <p><strong>Symbol:</strong> {{symbol}}</p>
            <p><strong>Direction:</strong> {{direction}}</p>
            <p><strong>Entry:</strong> ₹{{entry}}</p>
            <p><strong>Target:</strong> ₹{{target}}</p>
            <p><strong>Stop Loss:</strong> ₹{{stop_loss}}</p>
            <p><strong>Confidence:</strong> {{confidence}}%</p>
        </div>
        <p>
            <a href="https://tradosphere.com/dashboard" class="button">View Signal</a>
        </p>
        <p>Manage notification settings in your profile.</p>
    </div>
</body>
</html>
        '''
    }
}

def get_template(template_name):
    """Get email template by name"""
    return EMAIL_TEMPLATES.get(template_name)

def render_template(template_name, **variables):
    """Render template with variables"""
    template = get_template(template_name)
    if not template:
        return None

    subject = template['subject']
    html = template['html']

    # Simple variable substitution
    for key, value in variables.items():
        subject = subject.replace(f'{{{{{key}}}}}', str(value))
        html = html.replace(f'{{{{{key}}}}}', str(value))

    return {
        'subject': subject,
        'html': html
    }
