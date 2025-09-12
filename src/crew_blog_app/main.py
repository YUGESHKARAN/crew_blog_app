import os   
import re
import traceback
from datetime import datetime
from crew_blog_app.crew import CrewBase
# from crew import TheConsultantCrew, Content
from crew_blog_app.crew import TheConsultantCrew, Content


def setup_production_storage():
    """Configure storage for production deployment"""
    if os.environ.get("ENVIRONMENT") == "production":
        storage_dir = os.environ.get("CREWAI_STORAGE_DIR", "/app/storage")
    else:
        storage_dir = os.environ.get("CREWAI_STORAGE_DIR", "./storage")
    
    os.environ["CREWAI_STORAGE_DIR"] = storage_dir
    
    # Create resources directory structure
    resources_path = os.path.join(storage_dir, "resources", "draft")
    os.makedirs(resources_path, exist_ok=True)
    
    return resources_path, storage_dir

def sanitize_filename(topic):
    """Convert topic to safe filename"""
    # Remove special characters and replace spaces with underscores
    safe_name = re.sub(r'[^\w\s-]', '', topic)
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    return safe_name.lower().strip('_')

# Initialize storage paths
RESOURCES_PATH, STORAGE_DIR = setup_production_storage()


def run_crew(inputs: dict):
    """
    Run the crew with dynamic inputs
    """
    # Validate inputs against your BaseModel
    content_fields = {
        "domain_name": inputs.get("domain_name"),
        "topic": inputs.get("topic"),
        "learning_level": inputs.get("learning_level"),
        "preferred_language": inputs.get("preferred_language"),
        "estimated_time": inputs.get("estimated_time"),
        "current_date": inputs.get("current_date"),
        "resources_path": inputs.get("resources_path"),  # Add this to Content model
        "research_filename": inputs.get("research_filename"),
        "calendar_filename": inputs.get("calendar_filename"),
        "safe_topic": inputs.get("safe_topic")
    }
    
    # Create crew instance
    content_inputs = Content(**content_fields)

    crew_instance = TheConsultantCrew()
    
    # Execute crew with validated inputs
    result = crew_instance.crew().kickoff(inputs=content_inputs.dict())
    
    return result

def run():
    """
    Run the crew - required function for CrewAI CLI
    Returns same response structure as Flask app
    """
    try:
        # Default inputs for CLI execution (matching your Flask app structure)
        data = {
            "domain_name": "Blockchain",
            "topic": "Smart Contracts & dApps", 
            "learning_level": "beginner to advanced",
            "preferred_language": "English",
            "estimated_time": "2 months",
            "current_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        print(f"Using data: {data}")
        print(f"Using storage directory: {STORAGE_DIR}")
        print(f"Resources path: {RESOURCES_PATH}")
        
        # Create topic-specific filename (same logic as Flask app)
        topic = data.get('topic', 'default_topic')
        safe_topic = sanitize_filename(topic)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        research_filename = f"{safe_topic}_{timestamp}"
        calendar_filename = f"content_calendar_{safe_topic}_{timestamp}.md"
        
        # Enhanced inputs (same as Flask app)
        enhanced_inputs = data.copy()
        enhanced_inputs.update({
            'research_filename': research_filename,
            'calendar_filename': calendar_filename,
            'resources_path': RESOURCES_PATH,
            'safe_topic': safe_topic
        })
        
        result = run_crew(enhanced_inputs)
        
        # Read the topic-specific content_calendar file (same as Flask app)
        calendar_file_path = os.path.join(RESOURCES_PATH, calendar_filename)
        research_file_path = os.path.join(RESOURCES_PATH, f"research_consultant_{safe_topic}_{timestamp}.md")
        
        response_data = {
            "status": "success",
            # "summary": str(result),
            "files_created": [],
            "storage_info": {
                "storage_dir": STORAGE_DIR,
                "resources_path": RESOURCES_PATH,
                "topic": safe_topic,
                "timestamp": timestamp
            }
        }
        
        # Check for calendar file
        if os.path.exists(calendar_file_path):
            with open(calendar_file_path, 'r', encoding='utf-8') as file:
                calendar_content = file.read()
            response_data["content_calendar"] = calendar_content
            response_data["files_created"].append({
                "type": "calendar",
                "filename": calendar_filename,
                "path": calendar_file_path
            })
            print(f"✅ Calendar file found: {calendar_file_path}")
        else:
            print(f"❌ Calendar file not found: {calendar_file_path}")
        
        # Check for research file
        if os.path.exists(research_file_path):
            with open(research_file_path, 'r', encoding='utf-8') as file:
                research_content = file.read()
            response_data["research_report"] = research_content
            response_data["files_created"].append({
                "type": "research",
                "filename": f"research_consultant_{safe_topic}_{timestamp}.md",
                "path": research_file_path
            })
            print(f"✅ Research file found: {research_file_path}")
        else:
            print(f"❌ Research file not found: {research_file_path}")
        
        if not response_data["files_created"]:
            response_data["status"] = "partial_success"
            response_data["message"] = f"Crew completed but no files found in {RESOURCES_PATH}"
        
        print("\n" + "="*50)
        print("CREW EXECUTION COMPLETED")
        print("="*50)
        print(f"Status: {response_data['status']}")
        print(f"Files created: {len(response_data['files_created'])}")
        
        for file_info in response_data["files_created"]:
            print(f"  - {file_info['type']}: {file_info['filename']}")
        
        if "content_calendar" in response_data:
            print(f"\n📅 CONTENT CALENDAR:")
            print("-" * 30)
            print(response_data["content_calendar"][:500] + "..." if len(response_data["content_calendar"]) > 500 else response_data["content_calendar"])
        
        if "research_report" in response_data:
            print(f"\n📊 RESEARCH REPORT:")
            print("-" * 30)
            print(response_data["research_report"][:500] + "..." if len(response_data["research_report"]) > 500 else response_data["research_report"])
        
        print("="*50)
        
        return response_data
        
    except Exception as e:
        # Print full traceback for debugging (same as Flask app)
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        
        error_response = {
            "status": "error", 
            "message": str(e),
            "traceback": traceback.format_exc(),
            "storage_info": {
                "storage_dir": STORAGE_DIR,
                "resources_path": RESOURCES_PATH
            }
        }
        
        print("\n" + "="*50)
        print("CREW EXECUTION FAILED")
        print("="*50)
        print(f"Error: {error_response['message']}")
        print("="*50)
        
        return error_response

if __name__ == "__main__":
    # For local testing - this will be replaced by API inputs in deployment
    result = run()