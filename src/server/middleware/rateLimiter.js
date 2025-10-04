import rateLimit from 'express-rate-limit';

export const emailRateLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: process.env.EMAIL_RATE_LIMIT || 5,
  message: 'Too many email requests, please try again later',
  standardHeaders: true,
  legacyHeaders: false,
});

// Then in emailRoutes.js:
import { emailRateLimiter } from '../middleware/rateLimiter';

router.post('/send', emailRateLimiter, async (req, res) => {
  // ... existing code ...
});
