// Add near other route imports
import emailRouter from './api/email';

// Add after other app.use() calls
app.use('/api/email', emailRouter);
