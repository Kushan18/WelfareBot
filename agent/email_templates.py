"""Email templates for WelfareBot notifications."""
from datetime import datetime


def get_reminder_template(scheme_name: str, deadline: datetime, days_before: int) -> tuple:
    """Get email template for deadline reminder.
    
    Returns: (subject, plain_text_body, html_body)
    """
    deadline_str = deadline.strftime("%B %d, %Y")
    
    subject = f"Reminder: {scheme_name} deadline in {days_before} day{'s' if days_before > 1 else ''}"
    
    plain_text = f"""
Dear WelfareBot User,

This is a friendly reminder that the application deadline for {scheme_name} is approaching.

Scheme: {scheme_name}
Deadline: {deadline_str}
Time remaining: {days_before} day{'s' if days_before > 1 else ''}

Please ensure you submit your application before the deadline to avoid missing out on this opportunity.

If you have already applied, you can disregard this message.

Best regards,
WelfareBot Team
"""
    
    html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
        .scheme-name {{ font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
        .deadline {{ background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
        .deadline strong {{ color: #92400e; }}
        .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
        .button {{ display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📢 Deadline Reminder</h1>
        </div>
        <div class="content">
            <p class="scheme-name">{scheme_name}</p>
            <p>This is a friendly reminder that the application deadline is approaching.</p>
            
            <div class="deadline">
                <strong>⏰ Deadline: {deadline_str}</strong><br>
                <strong>Time remaining: {days_before} day{'s' if days_before > 1 else ''}</strong>
            </div>
            
            <p>Please ensure you submit your application before the deadline to avoid missing out on this opportunity.</p>
            
            <p>If you have already applied, you can disregard this message.</p>
            
            <a href="#" class="button">View Scheme Details</a>
            
            <div class="footer">
                <p>Best regards,<br>WelfareBot Team</p>
                <p style="font-size: 12px; margin-top: 20px;">You received this email because you subscribed to deadline reminders.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    return subject, plain_text, html_body


def get_welcome_template(user_name: str) -> tuple:
    """Get welcome email template for new users.
    
    Returns: (subject, plain_text_body, html_body)
    """
    subject = "Welcome to WelfareBot!"
    
    plain_text = f"""
Dear {user_name},

Welcome to WelfareBot! We're excited to help you discover government welfare schemes you may be eligible for.

With WelfareBot, you can:
- Discover schemes based on your profile
- Get personalized recommendations
- Track application deadlines
- Receive timely reminders

If you have any questions, feel free to reach out through our chat interface.

Best regards,
WelfareBot Team
"""
    
    html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
        .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
        .welcome {{ font-size: 28px; font-weight: bold; margin-bottom: 10px; }}
        .features {{ margin: 20px 0; }}
        .features li {{ margin: 10px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Welcome to WelfareBot!</h1>
        </div>
        <div class="content">
            <p>Dear {user_name},</p>
            <p>We're excited to help you discover government welfare schemes you may be eligible for.</p>
            
            <h3>With WelfareBot, you can:</h3>
            <ul class="features">
                <li>✅ Discover schemes based on your profile</li>
                <li>✅ Get personalized recommendations</li>
                <li>✅ Track application deadlines</li>
                <li>✅ Receive timely reminders</li>
            </ul>
            
            <p>If you have any questions, feel free to reach out through our chat interface.</p>
            
            <div class="footer">
                <p>Best regards,<br>WelfareBot Team</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    return subject, plain_text, html_body


def get_new_scheme_template(scheme_name: str, scheme_description: str) -> tuple:
    """Get email template for new scheme notification.
    
    Returns: (subject, plain_text_body, html_body)
    """
    subject = f"New Scheme Available: {scheme_name}"
    
    plain_text = f"""
Dear WelfareBot User,

A new government welfare scheme has been added that might interest you.

Scheme: {scheme_name}
Description: {scheme_description}

Log in to WelfareBot to check if you're eligible and apply!

Best regards,
WelfareBot Team
"""
    
    html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
        .scheme-name {{ font-size: 24px; font-weight: bold; color: #059669; margin-bottom: 10px; }}
        .description {{ background: #ecfdf5; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981; }}
        .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🆕 New Scheme Available</h1>
        </div>
        <div class="content">
            <p class="scheme-name">{scheme_name}</p>
            <p>A new government welfare scheme has been added that might interest you.</p>
            
            <div class="description">
                <strong>Description:</strong><br>
                {scheme_description}
            </div>
            
            <p>Log in to WelfareBot to check if you're eligible and apply!</p>
            
            <div class="footer">
                <p>Best regards,<br>WelfareBot Team</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    return subject, plain_text, html_body
