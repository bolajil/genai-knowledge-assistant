import express from 'express';
import emailRouter from './routes/emailRoutes';

const app = express();
app.use(express.json());

// Add email routes
app.use('/api/email', emailRouter);

// ... other server setup code ...

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
