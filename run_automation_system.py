"""
VaultMind Automation System Launcher
Starts all automation components: monitoring, backups, and AI agents
"""

import logging
import asyncio
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create logs directory
Path('logs').mkdir(exist_ok=True)


def start_metrics_server():
    """Start Prometheus metrics server"""
    try:
        from utils.monitoring.metrics import metrics
        metrics.start_metrics_server(port=8000)
        metrics.set_system_info(version="1.0.0", environment="production")
        logger.info("✅ Metrics server started on http://localhost:8000/metrics")
    except Exception as e:
        logger.error(f"❌ Failed to start metrics server: {e}")


async def start_agents():
    """Start AI agent system"""
    try:
        from app.agents.agent_orchestrator import orchestrator, HealthMonitorAgent, BackupAgent, MetricsCollectorAgent
        
        # Register agents with custom intervals
        orchestrator.register_agent(HealthMonitorAgent({
            'interval_seconds': 60,  # Check health every minute
            'enabled': True
        }))
        
        orchestrator.register_agent(BackupAgent({
            'interval_seconds': 3600,  # Backup every hour
            'enabled': True
        }))
        
        orchestrator.register_agent(MetricsCollectorAgent({
            'interval_seconds': 300,  # Collect metrics every 5 minutes
            'enabled': True
        }))
        
        logger.info("✅ AI agents registered")
        
        # Start all agents
        await orchestrator.start_all()
        logger.info("✅ All AI agents started")
        
        # Keep running
        while orchestrator.running:
            await asyncio.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("Shutting down agents...")
        await orchestrator.stop_all()
    except Exception as e:
        logger.error(f"❌ Agent system error: {e}")
        raise


def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    
    try:
        import prometheus_client
    except ImportError:
        missing.append('prometheus-client')
    
    try:
        import redis
    except ImportError:
        missing.append('redis')
    
    try:
        import celery
    except ImportError:
        missing.append('celery')
    
    if missing:
        logger.error(f"❌ Missing dependencies: {', '.join(missing)}")
        logger.error("Install with: pip install " + " ".join(missing))
        return False
    
    return True


def main():
    """Main entry point"""
    logger.info("="*70)
    logger.info("VaultMind Automation System")
    logger.info("="*70)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Start metrics server
    start_metrics_server()
    
    # Start AI agents
    logger.info("Starting AI agent system...")
    try:
        asyncio.run(start_agents())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
