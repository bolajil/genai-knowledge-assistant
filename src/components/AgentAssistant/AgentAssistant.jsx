// In your main Agent Assistant component
import EmailControls from './EmailControls';

export default function AgentAssistant() {
  const [agentResponse, setAgentResponse] = useState('');
  const [userQuestion, setUserQuestion] = useState('');
  
  // ... existing query handling logic ...

  return (
    <div className="agent-assistant">
      {/* Existing UI elements */}
      <div className="query-section">
        <input 
          className="question-input"
          value={userQuestion}
          onChange={(e) => setUserQuestion(e.target.value)}
          placeholder="What are the most important pieces of this document"
        />
        <button onClick={handleQuery}>Submit</button>
      </div>
      
      {agentResponse && (
        <div className="response-section">
          <div className="agent-response">
            {/* Render your agent response here */}
            {agentResponse}
          </div>
          
          {/* Add Email Controls */}
          <EmailControls 
            agentResponse={agentResponse} 
            userQuestion={userQuestion} 
          />
        </div>
      )}
    </div>
  );
}
