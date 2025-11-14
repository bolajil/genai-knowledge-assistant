"""
AI Agent Orchestrator for VaultMind
Manages and coordinates multiple AI agents
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class AgentStatus:
    """Agent status constants"""
    IDLE = 'idle'
    RUNNING = 'running'
    PAUSED = 'paused'
    ERROR = 'error'
    STOPPED = 'stopped'


class BaseAgent:
    """Base class for all AI agents"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self.last_run = None
        self.run_count = 0
        self.error_count = 0
        self.enabled = self.config.get('enabled', True)
    
    async def start(self):
        """Start the agent"""
        if not self.enabled:
            logger.info(f"Agent {self.name} is disabled")
            return
        
        self.status = AgentStatus.RUNNING
        logger.info(f"Agent {self.name} started")
        
        try:
            await self.run()
            self.run_count += 1
            self.last_run = datetime.utcnow()
        except Exception as e:
            self.error_count += 1
            self.status = AgentStatus.ERROR
            logger.error(f"Agent {self.name} error: {e}")
            raise
        finally:
            if self.status == AgentStatus.RUNNING:
                self.status = AgentStatus.IDLE
    
    async def run(self):
        """Main agent logic (to be implemented by subclasses)"""
        raise NotImplementedError("Subclasses must implement run()")
    
    def pause(self):
        """Pause the agent"""
        self.status = AgentStatus.PAUSED
        logger.info(f"Agent {self.name} paused")
    
    def resume(self):
        """Resume the agent"""
        self.status = AgentStatus.IDLE
        logger.info(f"Agent {self.name} resumed")
    
    def stop(self):
        """Stop the agent"""
        self.status = AgentStatus.STOPPED
        logger.info(f"Agent {self.name} stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            'name': self.name,
            'status': self.status,
            'enabled': self.enabled,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'run_count': self.run_count,
            'error_count': self.error_count
        }


class AgentOrchestrator:
    """
    Orchestrates multiple AI agents
    Manages agent lifecycle, scheduling, and coordination
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.agents: Dict[str, BaseAgent] = {}
        self.running = False
        self.tasks: List[asyncio.Task] = []
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator"""
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
    
    def unregister_agent(self, agent_name: str):
        """Unregister an agent"""
        if agent_name in self.agents:
            self.agents[agent_name].stop()
            del self.agents[agent_name]
            logger.info(f"Unregistered agent: {agent_name}")
    
    async def start_all(self):
        """Start all registered agents"""
        self.running = True
        logger.info(f"Starting {len(self.agents)} agents")
        
        for agent in self.agents.values():
            if agent.enabled:
                task = asyncio.create_task(self._run_agent_loop(agent))
                self.tasks.append(task)
        
        logger.info("All agents started")
    
    async def _run_agent_loop(self, agent: BaseAgent):
        """Run agent in a loop with configured interval"""
        interval = agent.config.get('interval_seconds', 300)  # Default 5 minutes
        
        while self.running and agent.status != AgentStatus.STOPPED:
            if agent.status == AgentStatus.PAUSED:
                await asyncio.sleep(10)
                continue
            
            try:
                await agent.start()
            except Exception as e:
                logger.error(f"Agent {agent.name} failed: {e}")
                
                # Exponential backoff on errors
                if agent.error_count > 3:
                    logger.warning(f"Agent {agent.name} has {agent.error_count} errors, increasing interval")
                    interval = min(interval * 2, 3600)  # Max 1 hour
            
            await asyncio.sleep(interval)
    
    async def stop_all(self):
        """Stop all agents"""
        self.running = False
        logger.info("Stopping all agents")
        
        for agent in self.agents.values():
            agent.stop()
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        logger.info("All agents stopped")
    
    def pause_agent(self, agent_name: str):
        """Pause a specific agent"""
        if agent_name in self.agents:
            self.agents[agent_name].pause()
    
    def resume_agent(self, agent_name: str):
        """Resume a specific agent"""
        if agent_name in self.agents:
            self.agents[agent_name].resume()
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            'running': self.running,
            'agent_count': len(self.agents),
            'agents': {
                name: agent.get_status()
                for name, agent in self.agents.items()
            }
        }
    
    def get_agent_status(self, agent_name: str) -> Optional[Dict]:
        """Get status of a specific agent"""
        if agent_name in self.agents:
            return self.agents[agent_name].get_status()
        return None


# Global orchestrator instance
orchestrator = AgentOrchestrator()


# Example agent implementations
class HealthMonitorAgent(BaseAgent):
    """Agent that monitors system health"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__('health_monitor', config)
    
    async def run(self):
        """Monitor system health"""
        from utils.monitoring.health_checks import health_checker
        from utils.monitoring.alerts import alert_manager, SEVERITY_CRITICAL, SEVERITY_WARNING
        
        logger.info("Running health check")
        health_status = health_checker.run_all_checks()
        
        # Check for unhealthy components
        for component, status in health_status.items():
            if status['status'] == 'unhealthy':
                alert_manager.send_alert(
                    severity=SEVERITY_CRITICAL,
                    title=f"{component} is unhealthy",
                    message=status.get('message', 'Component health check failed'),
                    metadata={'component': component, 'details': status.get('details', {})}
                )
            elif status['status'] == 'degraded':
                alert_manager.send_alert(
                    severity=SEVERITY_WARNING,
                    title=f"{component} is degraded",
                    message=status.get('message', 'Component performance degraded'),
                    metadata={'component': component, 'details': status.get('details', {})}
                )


class BackupAgent(BaseAgent):
    """Agent that manages automated backups"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__('backup_agent', config)
    
    async def run(self):
        """Perform backup operations"""
        from utils.backup.backup_manager import BackupManager
        
        logger.info("Running backup operations")
        manager = BackupManager()
        
        # Determine what to backup based on schedule
        current_hour = datetime.now().hour
        
        if current_hour == 2:
            # Full backup at 2 AM
            result = manager.backup_all()
            logger.info(f"Full backup completed: {result}")
        else:
            # Incremental database backup
            result = manager.backup_databases()
            logger.info(f"Database backup completed: {result}")


class MetricsCollectorAgent(BaseAgent):
    """Agent that collects and updates metrics"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__('metrics_collector', config)
    
    async def run(self):
        """Collect system metrics"""
        from utils.monitoring.metrics import metrics
        from utils.monitoring.health_checks import health_checker
        
        logger.info("Collecting system metrics")
        
        # Update health metrics
        health_status = health_checker.run_all_checks()
        for component, status in health_status.items():
            is_healthy = status['status'] == 'healthy'
            metrics.update_vector_store_health(component, is_healthy)
        
        # Additional metrics collection can be added here


def start_agent_system(config: Optional[Dict] = None):
    """
    Start the AI agent system
    
    Usage:
        from app.agents.agent_orchestrator import start_agent_system
        asyncio.run(start_agent_system())
    """
    logger.info("Starting VaultMind AI Agent System")
    
    # Register agents
    orchestrator.register_agent(HealthMonitorAgent({'interval_seconds': 60}))
    orchestrator.register_agent(BackupAgent({'interval_seconds': 3600}))
    orchestrator.register_agent(MetricsCollectorAgent({'interval_seconds': 300}))
    
    # Start all agents
    return orchestrator.start_all()


if __name__ == '__main__':
    # Run the agent system
    asyncio.run(start_agent_system())
