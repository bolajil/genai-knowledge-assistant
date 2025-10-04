"""
User Feedback System

Implements user feedback collection and analysis for continuous improvement
of query results and system performance.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import sqlite3
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class FeedbackEntry:
    """User feedback entry"""
    id: str
    timestamp: datetime
    query: str
    response_text: str
    was_helpful: bool
    confidence_score: float
    retrieval_method: str
    source_documents: List[Dict[str, Any]]
    user_id: str = "anonymous"
    additional_feedback: str = ""
    improvement_suggestions: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'query': self.query,
            'response_text': self.response_text,
            'was_helpful': self.was_helpful,
            'confidence_score': self.confidence_score,
            'retrieval_method': self.retrieval_method,
            'source_documents': json.dumps(self.source_documents),
            'user_id': self.user_id,
            'additional_feedback': self.additional_feedback,
            'improvement_suggestions': json.dumps(self.improvement_suggestions or [])
        }

class FeedbackDatabase:
    """SQLite database for storing user feedback"""
    
    def __init__(self, db_path: str = "data/user_feedback.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize feedback database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        query TEXT NOT NULL,
                        response_text TEXT NOT NULL,
                        was_helpful BOOLEAN NOT NULL,
                        confidence_score REAL NOT NULL,
                        retrieval_method TEXT NOT NULL,
                        source_documents TEXT NOT NULL,
                        user_id TEXT DEFAULT 'anonymous',
                        additional_feedback TEXT DEFAULT '',
                        improvement_suggestions TEXT DEFAULT '[]',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better query performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON feedback(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_was_helpful ON feedback(was_helpful)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_query ON feedback(query)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON feedback(user_id)")
                
                conn.commit()
                logger.info(f"Feedback database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize feedback database: {e}")
    
    def store_feedback(self, feedback: FeedbackEntry) -> bool:
        """Store feedback entry in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                feedback_dict = feedback.to_dict()
                
                conn.execute("""
                    INSERT OR REPLACE INTO feedback 
                    (id, timestamp, query, response_text, was_helpful, confidence_score, 
                     retrieval_method, source_documents, user_id, additional_feedback, 
                     improvement_suggestions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    feedback_dict['id'],
                    feedback_dict['timestamp'],
                    feedback_dict['query'],
                    feedback_dict['response_text'],
                    feedback_dict['was_helpful'],
                    feedback_dict['confidence_score'],
                    feedback_dict['retrieval_method'],
                    feedback_dict['source_documents'],
                    feedback_dict['user_id'],
                    feedback_dict['additional_feedback'],
                    feedback_dict['improvement_suggestions']
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to store feedback: {e}")
            return False
    
    def get_feedback_by_query(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get feedback entries for similar queries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("""
                    SELECT * FROM feedback 
                    WHERE query LIKE ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (f"%{query}%", limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to retrieve feedback by query: {e}")
            return []
    
    def get_recent_feedback(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent feedback entries"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("""
                    SELECT * FROM feedback 
                    WHERE timestamp >= ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (cutoff_date, limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to retrieve recent feedback: {e}")
            return []
    
    def get_feedback_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get feedback statistics"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Total feedback count
                total_count = conn.execute(
                    "SELECT COUNT(*) FROM feedback WHERE timestamp >= ?", 
                    (cutoff_date,)
                ).fetchone()[0]
                
                # Helpful vs not helpful
                helpful_count = conn.execute(
                    "SELECT COUNT(*) FROM feedback WHERE timestamp >= ? AND was_helpful = 1", 
                    (cutoff_date,)
                ).fetchone()[0]
                
                # Average confidence score
                avg_confidence = conn.execute(
                    "SELECT AVG(confidence_score) FROM feedback WHERE timestamp >= ?", 
                    (cutoff_date,)
                ).fetchone()[0] or 0
                
                # Most common retrieval methods
                methods = conn.execute("""
                    SELECT retrieval_method, COUNT(*) as count 
                    FROM feedback 
                    WHERE timestamp >= ? 
                    GROUP BY retrieval_method 
                    ORDER BY count DESC
                """, (cutoff_date,)).fetchall()
                
                # Most problematic queries (low helpfulness)
                problematic_queries = conn.execute("""
                    SELECT query, COUNT(*) as count, AVG(confidence_score) as avg_confidence
                    FROM feedback 
                    WHERE timestamp >= ? AND was_helpful = 0
                    GROUP BY query 
                    HAVING count >= 2
                    ORDER BY count DESC, avg_confidence ASC
                    LIMIT 10
                """, (cutoff_date,)).fetchall()
                
                return {
                    'total_feedback': total_count,
                    'helpful_feedback': helpful_count,
                    'helpfulness_rate': helpful_count / total_count if total_count > 0 else 0,
                    'average_confidence': avg_confidence,
                    'retrieval_methods': [{'method': m[0], 'count': m[1]} for m in methods],
                    'problematic_queries': [
                        {'query': q[0], 'count': q[1], 'avg_confidence': q[2]} 
                        for q in problematic_queries
                    ]
                }
                
        except Exception as e:
            logger.error(f"Failed to get feedback statistics: {e}")
            return {}

class UserFeedbackSystem:
    """Main user feedback system"""
    
    def __init__(self, db_path: str = "data/user_feedback.db"):
        self.database = FeedbackDatabase(db_path)
        self.feedback_cache = {}  # In-memory cache for recent feedback
    
    def log_user_feedback(
        self,
        query: str,
        response_text: str,
        was_helpful: bool,
        retrieved_docs: List[Dict[str, Any]],
        confidence_score: float = 0.0,
        retrieval_method: str = "unknown",
        user_id: str = "anonymous",
        additional_feedback: str = ""
    ) -> str:
        """
        Log user feedback for a query response
        
        Returns:
            Feedback ID for tracking
        """
        try:
            import uuid
            feedback_id = str(uuid.uuid4())
            
            feedback = FeedbackEntry(
                id=feedback_id,
                timestamp=datetime.now(),
                query=query,
                response_text=response_text,
                was_helpful=was_helpful,
                confidence_score=confidence_score,
                retrieval_method=retrieval_method,
                source_documents=retrieved_docs,
                user_id=user_id,
                additional_feedback=additional_feedback
            )
            
            # Store in database
            success = self.database.store_feedback(feedback)
            
            if success:
                # Update cache
                self.feedback_cache[feedback_id] = feedback
                logger.info(f"Feedback logged: {feedback_id} - {'Helpful' if was_helpful else 'Not helpful'}")
                
                # Trigger analysis if this is negative feedback
                if not was_helpful:
                    self._analyze_negative_feedback(feedback)
                
                return feedback_id
            else:
                logger.error("Failed to store feedback in database")
                return ""
                
        except Exception as e:
            logger.error(f"Failed to log user feedback: {e}")
            return ""
    
    def _analyze_negative_feedback(self, feedback: FeedbackEntry):
        """Analyze negative feedback and generate improvement suggestions"""
        try:
            # Look for patterns in negative feedback
            similar_feedback = self.database.get_feedback_by_query(feedback.query, limit=5)
            negative_feedback = [f for f in similar_feedback if not f['was_helpful']]
            
            if len(negative_feedback) >= 2:
                logger.warning(f"Multiple negative feedback entries for similar queries to: '{feedback.query}'")
                
                # Generate improvement suggestions
                suggestions = self._generate_improvement_suggestions(feedback, negative_feedback)
                feedback.improvement_suggestions = suggestions
                
                # Update database with suggestions
                self.database.store_feedback(feedback)
                
        except Exception as e:
            logger.error(f"Failed to analyze negative feedback: {e}")
    
    def _generate_improvement_suggestions(
        self, 
        current_feedback: FeedbackEntry, 
        similar_negative_feedback: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate improvement suggestions based on feedback patterns"""
        suggestions = []
        
        # Analyze confidence scores
        avg_confidence = sum(f['confidence_score'] for f in similar_negative_feedback) / len(similar_negative_feedback)
        
        if avg_confidence < 0.5:
            suggestions.append("Consider improving query expansion for better document matching")
        
        if current_feedback.confidence_score < 0.3:
            suggestions.append("Query may be too vague - implement query clarification prompts")
        
        # Analyze query patterns
        query_words = current_feedback.query.lower().split()
        
        if len(query_words) <= 2:
            suggestions.append("Encourage users to provide more detailed queries")
        
        if any(word in current_feedback.query.lower() for word in ['all', 'everything', 'about']):
            suggestions.append("Implement query refinement for overly broad queries")
        
        # Analyze retrieval method effectiveness
        method_counts = {}
        for f in similar_negative_feedback:
            method = f['retrieval_method']
            method_counts[method] = method_counts.get(method, 0) + 1
        
        if method_counts:
            worst_method = max(method_counts.items(), key=lambda x: x[1])[0]
            suggestions.append(f"Consider improving or replacing '{worst_method}' retrieval method")
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def get_query_performance_insights(self, query: str) -> Dict[str, Any]:
        """Get performance insights for a specific query"""
        try:
            feedback_entries = self.database.get_feedback_by_query(query, limit=20)
            
            if not feedback_entries:
                return {"message": "No feedback data available for this query"}
            
            total_entries = len(feedback_entries)
            helpful_entries = sum(1 for f in feedback_entries if f['was_helpful'])
            avg_confidence = sum(f['confidence_score'] for f in feedback_entries) / total_entries
            
            # Get common improvement suggestions
            all_suggestions = []
            for entry in feedback_entries:
                suggestions = json.loads(entry.get('improvement_suggestions', '[]'))
                all_suggestions.extend(suggestions)
            
            # Count suggestion frequency
            suggestion_counts = {}
            for suggestion in all_suggestions:
                suggestion_counts[suggestion] = suggestion_counts.get(suggestion, 0) + 1
            
            top_suggestions = sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            return {
                'total_feedback': total_entries,
                'helpfulness_rate': helpful_entries / total_entries,
                'average_confidence': avg_confidence,
                'top_improvement_suggestions': [s[0] for s in top_suggestions],
                'recommendation': self._get_query_recommendation(helpful_entries / total_entries, avg_confidence)
            }
            
        except Exception as e:
            logger.error(f"Failed to get query insights: {e}")
            return {"error": str(e)}
    
    def _get_query_recommendation(self, helpfulness_rate: float, avg_confidence: float) -> str:
        """Get recommendation based on query performance"""
        if helpfulness_rate >= 0.8 and avg_confidence >= 0.7:
            return "Query performs well - no changes needed"
        elif helpfulness_rate < 0.5:
            return "Query has low helpfulness - consider query expansion or result filtering improvements"
        elif avg_confidence < 0.5:
            return "Query has low confidence scores - improve document matching or re-ranking"
        else:
            return "Query has moderate performance - minor improvements recommended"
    
    def get_system_feedback_report(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive feedback report for system analysis"""
        try:
            stats = self.database.get_feedback_statistics(days)
            recent_feedback = self.database.get_recent_feedback(days, limit=50)
            
            # Analyze trends
            daily_feedback = {}
            for entry in recent_feedback:
                date = entry['timestamp'][:10]  # Extract date part
                if date not in daily_feedback:
                    daily_feedback[date] = {'total': 0, 'helpful': 0}
                daily_feedback[date]['total'] += 1
                if entry['was_helpful']:
                    daily_feedback[date]['helpful'] += 1
            
            # Calculate daily helpfulness rates
            daily_rates = {}
            for date, counts in daily_feedback.items():
                daily_rates[date] = counts['helpful'] / counts['total'] if counts['total'] > 0 else 0
            
            report = {
                'period_days': days,
                'overall_statistics': stats,
                'daily_feedback_counts': daily_feedback,
                'daily_helpfulness_rates': daily_rates,
                'trends': {
                    'improving': len([r for r in daily_rates.values() if r > 0.7]),
                    'declining': len([r for r in daily_rates.values() if r < 0.5])
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate feedback report: {e}")
            return {"error": str(e)}
    
    def export_feedback_data(self, output_file: str, days: int = 30) -> bool:
        """Export feedback data to JSON file"""
        try:
            feedback_data = self.database.get_recent_feedback(days, limit=1000)
            stats = self.database.get_feedback_statistics(days)
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'period_days': days,
                'statistics': stats,
                'feedback_entries': feedback_data
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Feedback data exported to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export feedback data: {e}")
            return False

def get_user_feedback_system(db_path: str = "data/user_feedback.db") -> UserFeedbackSystem:
    """Get user feedback system instance"""
    return UserFeedbackSystem(db_path)

def log_query_feedback(
    query: str,
    response: str,
    was_helpful: bool,
    source_docs: List[Dict[str, Any]] = None,
    confidence: float = 0.0,
    method: str = "unknown"
) -> str:
    """Convenience function to log feedback"""
    feedback_system = get_user_feedback_system()
    return feedback_system.log_user_feedback(
        query=query,
        response_text=response,
        was_helpful=was_helpful,
        retrieved_docs=source_docs or [],
        confidence_score=confidence,
        retrieval_method=method
    )
