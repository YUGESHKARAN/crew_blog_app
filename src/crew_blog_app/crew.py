import os
from typing import List
from crewai import Crew, Agent, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

from crewai_tools import SerperDevTool, ScrapeWebsiteTool, DirectoryReadTool, FileReadTool, FileWriterTool, YoutubeChannelSearchTool
from pydantic import BaseModel, Field,ConfigDict
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime
_ = load_dotenv()  # Load environment variables from .env file

llm = LLM(
# model="gemini/gemini-2.0-flash-001",
model="gemini/gemini-2.5-flash-lite",

temperature=0.5,
api_key=os.getenv("GOOGLE_API_KEY")
)

# Production configuration
def setup_production_storage():
    """Configure storage for production deployment"""
    # Set storage directory for production
    storage_dir = os.environ.get("CREWAI_STORAGE_DIR", "/app/storage")
    os.environ["CREWAI_STORAGE_DIR"] = storage_dir
    
    # Create resources directory structure
    resources_path = os.path.join(storage_dir, "resources", "draft")
    os.makedirs(resources_path, exist_ok=True)
    
    return resources_path

# class Content(BaseModel):
#     model_config = ConfigDict(
#         # Add any configuration you need
#         validate_assignment=True
#     )
#     domain_name: str = Field(..., description="donain name of the course content")
#     topic: str = Field(..., description="specified topic in the domain")
#     learning_level: str = Field(..., description="learning level (beginner, intermediate, advanced)")
#     preferred_language: str = Field(..., description="preferred language for the content (English, Spanish, etc.)")
#     estimated_time: str = Field(..., description="estimated time duration of the course (e.g., 4 weeks, 3 months)")
#     current_date: str = Field(..., description="the current date")

# class Content(BaseModel):
#     model_config = ConfigDict(
#         validate_assignment=True
#     )
#     domain_name: str = Field(default="General", description="domain name of the course content")
#     topic: str = Field(default="Default Topic", description="specified topic in the domain")
#     learning_level: Optional[str] = Field(default="beginner", description="learning level (beginner, intermediate, advanced)")
#     preferred_language: Optional[str] = Field(default="English", description="preferred language for the content")
#     estimated_time: Optional[str] = Field(default="1 month", description="estimated time duration of the course")
#     current_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"), description="the current date")


class Content(BaseModel):
    """Input schema for the crew"""
    model_config = ConfigDict(
        validate_assignment=True
    )
    domain_name: str = Field(
        default="General",
        description="Domain name of the course content"
    )
    topic: str = Field(
        default="Default Topic", 
        description="Specified topic in the domain"
    )
    learning_level: str = Field(
        default="beginner",
        description="Learning level (beginner, intermediate, advanced)"
    )
    preferred_language: str = Field(
        default="English",
        description="Preferred language for the content (English, Spanish, etc.)"
    )
    estimated_time: str = Field(
        default="1 month",
        description="Estimated time duration of the course (e.g., 4 weeks, 3 months)"
    )
    current_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d"),
        description="The current date"
    )
    resources_path: str = Field(
        default="./storage/resources/draft",
        description="Path to the resources directory for file storage"
    )
    research_filename: Optional[str] = Field(
        default=None,
        description="Filename for the research report output"
    )
    calendar_filename: Optional[str] = Field(
        default=None,
        description="Filename for the content calendar output"
    )
    safe_topic: Optional[str] = Field(
        default=None,
        description="Sanitized topic name for file naming"
    )

@CrewBase
class TheConsultantCrew():
    """A crew to create day wise content for a programming course."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    def __init__(self):
        # Remove super().__init__() for CrewBase
        self.resources_path = setup_production_storage()
        print(f"Crew initialized with resources path: {self.resources_path}")

    def inputs(self) -> type[BaseModel]:
        """Return the input schema for the crew"""
        return Content
    
    @agent
    def research_development(self)-> Agent:
         return Agent(
            config=self.agents_config['research_development'],
            tools=[
                SerperDevTool(),
                ScrapeWebsiteTool(),
                # DirectoryReadTool('resources/draft'),
                DirectoryReadTool(directory=self.resources_path),
                FileWriterTool(),
                FileReadTool()
            ],
            reasoning=False,
            inject_date=True,
            llm=llm,
            allow_delegation=True, # Reduced to prevent memory overhead
            max_rpm=3,
            cache=True,  # Enable caching
            respect_context_window=True,
            max_iter=10, # Limit iterations (default: 25)
            max_execution_time=1800 # 30 minutes timeout
        )
    
    @agent
    def content_creator(self)-> Agent:
        return Agent(
            config=self.agents_config['content_creator'],
            tools=[
                # SerperDevTool(),
                # ScrapeWebsiteTool(),
                # GithubSearchTool(),
                YoutubeChannelSearchTool(
                     config=dict(
                        llm=dict(
                            provider="google", # or google, openai, anthropic, llama2, ...
                            config=dict(
                                model="gemini/gemini-2.5-flash-lite",
                                # temperature=0.5,
                                # top_p=1,
                                # stream=true,
                            ),
                        ),
                        embedder=dict(
                            provider="google", # or openai, ollama, ...
                            config=dict(
                                model="models/embedding-001",
                                # task_type="retrieval_document",
                                # title="Embeddings",
                            ),
                        ),
                    )
                ),
                # DirectoryReadTool('resources/draft'),
                DirectoryReadTool(directory=self.resources_path),
                FileWriterTool(),
                FileReadTool()
            ],
            reasoning=True,
            inject_date=True,
            llm=llm,
            allow_delegation=True,
            max_rpm=3,
            cache=True,
            respect_context_window=True,
            max_iter=20,
            max_execution_time=1800

        )
  
    @agent
    def tasks_scheduler(self)-> Agent:
         return Agent(
            config=self.agents_config['tasks_scheduler'],
            tools=[
                # SerperDevTool(),
                # ScrapeWebsiteTool(),
                # DirectoryReadTool('resources/draft'),
                DirectoryReadTool(directory=self.resources_path),
                FileWriterTool(),
                FileReadTool()
            ],
            reasoning=False,
            inject_date=True,
            llm=llm,
            allow_delegation=True,
            max_rpm=3,
            cache=True,
            respect_context_window=True,
            max_iter=15,  # Lower for simpler scheduling tasks
            max_execution_time=1200  # 20 minutes
        )
    
    @task
    def research_consultant(self)-> Task:
        return Task(
            config=self.tasks_config['research_consultant'],
            agent=self.research_development(),
            max_iter=10,  # Limit task iterations
            max_execution_time=1800
        )
    
    @task
    def path_planner(self)-> Task:
        return Task(
            config=self.tasks_config['path_planner'],
            agent=self.research_development(),
            context=[self.research_consultant()],  # Wait for research to complete
            max_iter=8,
            max_execution_time=1200
        )
    
    @task
    def content_reviewer(self)-> Task:
        return Task(
            config=self.tasks_config['content_reviewer'],
            agent=self.content_creator(),
            context=[self.path_planner()],  # Wait for path planner to complete
            max_iter=12,
            max_execution_time=1500
        )
    @task
    def create_content_calendar(self)-> Task:
        return Task(
            config=self.tasks_config['create_content_calendar'],
            agent=self.tasks_scheduler(),
            context=[self.research_consultant(), self.path_planner(), self.content_reviewer()],  # Wait for all previous tasks
            max_iter=12,
            max_execution_time=1200
        )

    @crew
    def crew(self) -> Crew:
        """A crew designed to create day-wise learning content, covering a specified technology from scratch to advanced level."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            planning=False,
            reasoning=False,
            llm=llm,
            max_rpm=3,
            cache=True,  # Enable crew-level caching
            respect_context_window=True,
            max_execution_time=7200  # 2 hours total timeout
        )
