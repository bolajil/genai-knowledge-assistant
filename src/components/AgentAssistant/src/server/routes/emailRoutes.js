import express from 'express';
import nodemailer from 'nodemailer';

const router = express.Router();

// Create reusable transporter
const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST || 'smtp.gmail.com',
  port: process.env.SMTP_PORT || 587,
  secure: false,
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS
  }
});

// Email sending endpoint
router.post('/send', async (req, res) => {
  const { recipients, subject, content } = req.body;
  
  // Server-side email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const invalidEmails = recipients.filter(email => !emailRegex.test(email));
  
  if (invalidEmails.length > 0) {
    return res.status(400).json({
      success: false,
      message: `Invalid emails: ${invalidEmails.join(', ')}`
    });
  }

  try {
    // Send to all recipients
    await Promise.all(recipients.map(async (to) => {
      await transporter.sendMail({
        from: `"Agent Assistant" <${process.env.EMAIL_USER}>`,
        to,
        subject,
        html: formatEmailContent(content, subject)
      });
    }));
    
    res.json({ success: true, message: `Email sent to ${recipients.join(', ')}` });
  } catch (error) {
    console.error('Email send error:', error);
    res.status(500).json({
      success: false,
      message: `Failed to send email: ${error.message}`
    });
  }
});

// Helper to format email content
function formatEmailContent(content, subject) {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>${subject}</title>
      <style>
        /* Add your email styles here */
      </style>
    </head>
    <body>
      <div class="email-container">
        <div class="header">
          <h2>Agent Assistant Report</h2>
          <p><strong>Generated at:</strong> ${new Date().toLocaleString()}</p>
        </div>
        <div class="content">
          ${content}
        </div>
        <div class="footer">
          <p>This report was generated automatically by the Agent Assistant system.</p>
        </div>
      </div>
    </body>
    </html>
  `;
}

export default router;
