// Email Controls Component
export default function EmailControls({ agentResponse, userQuestion }) {
  const [recipients, setRecipients] = useState('');
  const [status, setStatus] = useState({ message: '', type: '' });

  const sendEmail = async () => {
    // Validate emails
    const emailList = recipients.split(',').map(email => email.trim());
    const invalidEmails = emailList.filter(email => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email));
    
    if (invalidEmails.length > 0) {
      setStatus({ 
        message: `Invalid emails: ${invalidEmails.join(', ')}`, 
        type: 'error' 
      });
      return;
    }

    setStatus({ message: 'Sending email...', type: 'processing' });
    
    try {
      const response = await fetch('/api/email/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipients: emailList,
          subject: `Agent Assistant Report: ${userQuestion.substring(0, 50)}${userQuestion.length > 50 ? '...' : ''}`,
          content: agentResponse
        })
      });

      const result = await response.json();
      if (result.success) {
        setStatus({ message: 'Email sent successfully!', type: 'success' });
      } else {
        setStatus({ message: `Failed: ${result.message}`, type: 'error' });
      }
    } catch (error) {
      setStatus({ message: `Network error: ${error.message}`, type: 'error' });
    }
  };

  return (
    <div className="email-controls">
      <h3>📧 Email Results</h3>
      
      <div className="email-input">
        <label>Recipients (comma-separated):</label>
        <input 
          type="text" 
          value={recipients}
          onChange={(e) => setRecipients(e.target.value)}
          placeholder="user1@example.com, user2@example.com"
        />
      </div>
      
      <div className="action-buttons">
        <button 
          onClick={sendEmail}
          disabled={status.type === 'processing'}
          className="send-button"
        >
          {status.type === 'processing' ? (
            <><Spinner /> Sending...</>
          ) : (
            <><i className="fas fa-paper-plane"></i> Send Email</>
          )}
        </button>
      </div>
      
      {status.message && (
        <div className={`status-message ${status.type}`}>
          {status.message}
        </div>
      )}
    </div>
  );
}
