import os
from typing import List
from crewai import Crew, Agent, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

from crewai_tools import SerperDevTool, ScrapeWebsiteTool, DirectoryReadTool, FileReadTool, FileWriterTool, YoutubeChannelSearchTool
from pydantic import BaseModel, Field,ConfigDict
from dotenv import load_dotenv

_ = load_dotenv()  # Load environment variables from .env file

llm = LLM(
# model="gemini/gemini-2.0-flash-001",
model="gemini/gemini-2.5-flash-lite",

temperature=0.5,
api_key=os.getenv("Google_API_KEY")
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

class Content(BaseModel):
    model_config = ConfigDict(
        # Add any configuration you need
        validate_assignment=True
    )
    domain_name: str = Field(..., description="donain name of the course content")
    topic: str = Field(..., description="specified topic in the domain")
    learning_level: str = Field(..., description="learning level (beginner, intermediate, advanced)")
    preferred_language: str = Field(..., description="preferred language for the content (English, Spanish, etc.)")
    estimated_time: str = Field(..., description="estimated time duration of the course (e.g., 4 weeks, 3 months)")
    current_date: str = Field(..., description="the current date")


@CrewBase
class TheConsultantCrew():
    """A crew to create day wise content for a programming course."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        super().__init__()
        self.resources_path = setup_production_storage()
        print(f"Crew initialized with resources path: {self.resources_path}")

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
            reasoning=True,
            inject_date=True,
            llm=llm,
            allow_delegation=True,
            max_rpm=1
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
            max_rpm=1
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
            reasoning=True,
            inject_date=True,
            llm=llm,
            allow_delegation=True,
            max_rpm=1
        )
    
    @task
    def research_consultant(self)-> Task:
        return Task(
            config=self.tasks_config['research_consultant'],
            agent=self.research_development(),
        )
    
    @task
    def path_planner(self)-> Task:
        return Task(
            config=self.tasks_config['path_planner'],
            agent=self.research_development(),
            context=[self.research_consultant()]  # Wait for research to complete
        )
    
    @task
    def content_reviewer(self)-> Task:
        return Task(
            config=self.tasks_config['content_reviewer'],
            agent=self.content_creator(),
            context=[self.path_planner()]  # Wait for path planner to complete
        )
    @task
    def create_content_calendar(self)-> Task:
        return Task(
            config=self.tasks_config['create_content_calendar'],
            agent=self.tasks_scheduler(),
            context=[self.research_consultant(), self.path_planner(), self.content_reviewer()]  # Wait for all previous tasks
        )

    @crew
    def consultantcrew(self) -> Crew:
        """A crew designed to create day-wise learning content, covering a specified technology from scratch to advanced level."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            planning=False,
            reasoning=False,
            llm=llm,
            max_rpm=1
        )
