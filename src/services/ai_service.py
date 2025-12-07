"""
AI Service
High-level service to interact with the AI Engine.
Initializes agents and routes requests.
"""

from typing import Optional

from src.ai_engine.agents.teacher import TeacherAgent
from src.ai_engine.core.agent import AgentContext
from src.ai_engine.core.llm import LLMClient
from src.services.agent_runs import AgentRunService
from src.db.database import get_session
from sqlmodel import Session

class AIService:
    def __init__(self):
        self.llm_client = LLMClient()
        # We need a way to get a session for the run service. 
        # For simplicity in this singleton-like service, we might need to pass it per request
        # or handle it differently. 
        # Here we will instantiate agents per request or keep them stateless.
        # Since agents hold state (tools), but tools are stateless mostly, we can reuse agents 
        # if we pass context in run().
        
        # However, AgentRunService needs a DB session.
        pass

    async def process_request(self, user_input: str, session_id: str, db: Session) -> str:
        """
        Process a user request through the Teacher Agent.
        """
        run_service = AgentRunService(db)
        
        # Create Run
        run = await run_service.create_run(session_id=session_id, input_text=user_input)
        
        # Initialize Context
        context = AgentContext(run_id=run.id, session_id=session_id)
        
        # Initialize Teacher
        teacher = TeacherAgent(self.llm_client, run_service)
        
        try:
            # Execute
            response = await teacher.run(context, user_input)
            
            # Update Run Status
            await run_service.complete_run(run.id, output_text=response)
            
            return response
            
        except Exception as e:
            await run_service.fail_run(run.id, error=str(e))
            raise e

# Global instance
ai_service = AIService()
