# import os   
# import re
# from datetime import datetime
# from crew_blog_app.crew import CrewBase
# # from crew import TheConsultantCrew, Content
# from crew_blog_app.crew import TheConsultantCrew, Content


# def setup_production_storage():
#     """Configure storage for production deployment"""
#     if os.environ.get("ENVIRONMENT") == "production":
#         storage_dir = os.environ.get("CREWAI_STORAGE_DIR", "/app/storage")
#     else:
#         storage_dir = os.environ.get("CREWAI_STORAGE_DIR", "./storage")
    
#     os.environ["CREWAI_STORAGE_DIR"] = storage_dir
    
#     # Create resources directory structure
#     resources_path = os.path.join(storage_dir, "resources", "draft")
#     os.makedirs(resources_path, exist_ok=True)
    
#     return resources_path, storage_dir

# def sanitize_filename(topic):
#     """Convert topic to safe filename"""
#     # Remove special characters and replace spaces with underscores
#     safe_name = re.sub(r'[^\w\s-]', '', topic)
#     safe_name = re.sub(r'[-\s]+', '_', safe_name)
#     return safe_name.lower().strip('_')

# # Initialize storage paths
# RESOURCES_PATH, STORAGE_DIR = setup_production_storage()


# def run_crew(inputs: dict):
#     """
#     Run the crew with dynamic inputs
#     """
#     # Validate inputs against your BaseModel
#     content_inputs = Content(**inputs)
    
#     # Create crew instance
#     crew_instance = TheConsultantCrew()
    
#     # Execute crew with validated inputs
#     result = crew_instance.consultantcrew().kickoff(inputs=content_inputs.dict())
    
#     return result

# if __name__ == "__main__":
#     # For local testing - this will be replaced by API inputs in deployment
#     test_inputs = {
#         "domain_name": "Data Science",
#         "topic": "Deep Learning", 
#         "learning_level": "beginner to advanced",
#         "preferred_language": "English",
#         "estimated_time": "2 months",
#         "current_date": datetime.now().strftime("%Y-%m-%d")
#     }
    
#     result = run_crew(test_inputs)
#     print("Crew execution completed:", result)

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
    Run the crew with dynamic inputs and enhanced file handling
    """
    try:
        # Debug: Print received data
        print(f"Received inputs: {inputs}")
        print(f"Using storage directory: {STORAGE_DIR}")
        print(f"Resources path: {RESOURCES_PATH}")
        
        if not inputs:
            return {
                "status": "error",
                "message": "No inputs provided"
            }
        
        # Add current date if not provided
        if 'current_date' not in inputs:
            inputs['current_date'] = datetime.now().strftime("%Y-%m-%d")
        
        # Validate inputs with detailed error handling
        try:
            content_inputs = Content(**inputs)
        except Exception as validation_error:
            return {
                "status": "error",
                "message": f"Validation error: {str(validation_error)}",
                "received_data": inputs
            }
        
        # Create topic-specific filename
        topic = inputs.get('topic', 'default_topic')
        safe_topic = sanitize_filename(topic)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Update the expected output in your task config to use topic-specific filename
        research_filename = f"{safe_topic}_{timestamp}"
        calendar_filename = f"content_calendar_{safe_topic}_{timestamp}.md"
        
        # Create crew instance
        crew_instance = TheConsultantCrew()
        
        # You can pass the filenames as additional inputs
        enhanced_inputs = content_inputs.dict()
        enhanced_inputs.update({
            'research_filename': research_filename,
            'calendar_filename': calendar_filename,
            'resources_path': RESOURCES_PATH,
            'safe_topic': safe_topic
        })
        
        # Execute crew with validated inputs
        result = crew_instance.consultantcrew().kickoff(inputs=enhanced_inputs)
        
        # Read the topic-specific content_calendar file
        calendar_file_path = os.path.join(RESOURCES_PATH, calendar_filename)
        research_file_path = os.path.join(RESOURCES_PATH, f"research_consultant_{safe_topic}_{timestamp}.md")
        
        response_data = {
            "status": "success",
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
        
        if not response_data["files_created"]:
            response_data["status"] = "partial_success"
            response_data["message"] = f"Crew completed but no files found in {RESOURCES_PATH}"
        
        return response_data
        
    except Exception as e:
        # Print full traceback for debugging
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        
        return {
            "status": "error", 
            "message": str(e),
            "traceback": traceback.format_exc(),
            "storage_info": {
                "storage_dir": STORAGE_DIR,
                "resources_path": RESOURCES_PATH
            }
        }

if __name__ == "__main__":
    # For local testing - this will be replaced by API inputs in deployment
    test_inputs = {
        "domain_name": "Data Science",
        "topic": "Deep Learning", 
        "learning_level": "beginner to advanced",
        "preferred_language": "English",
        "estimated_time": "2 months",
        "current_date": datetime.now().strftime("%Y-%m-%d")
    }
    
    result = run_crew(test_inputs)
    print("Crew execution completed:")
    print(result)



