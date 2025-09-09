import os
from flask import Flask, request, jsonify
from datetime import datetime
from crew_blog_app.crew import TheConsultantCrew, Content
from pathlib import Path
from flask_cors import CORS
import re
import traceback
app = Flask(__name__)

CORS(app)

# Production storage configuration
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

@app.route('/kickoff', methods=['POST'])
def kickoff_crew():
    try:
        # Get inputs from request
        data = request.get_json()
        
        # Debug: Print received data
        print(f"Received data: {data}")
        print(f"Using storage directory: {STORAGE_DIR}")
        print(f"Resources path: {RESOURCES_PATH}")
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data provided"
            }), 400
        
        # Add current date if not provided
        if 'current_date' not in data:
            data['current_date'] = datetime.now().strftime("%Y-%m-%d")
        
        # Validate inputs with detailed error handling
        try:
            content_inputs = Content(**data)
        except Exception as validation_error:
            return jsonify({
                "status": "error",
                "message": f"Validation error: {str(validation_error)}",
                "received_data": data
            }), 400
        
        # Create topic-specific filename
        topic = data.get('topic', 'default_topic')
        safe_topic = sanitize_filename(topic)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Update the expected output in your task config to use topic-specific filename
        research_filename = f"{safe_topic}_{timestamp}"
        calendar_filename = f"content_calendar_{safe_topic}_{timestamp}.md"
        
        # Run crew with topic-specific filenames
        crew_instance = TheConsultantCrew()
        
        # You can pass the filenames as additional inputs
        enhanced_inputs = content_inputs.dict()
        enhanced_inputs.update({
            'research_filename': research_filename,
            'calendar_filename': calendar_filename,
            'safe_topic': safe_topic
        })
        
        result = crew_instance.consultantcrew().kickoff(inputs=enhanced_inputs)
        
        # Read the topic-specific content_calendar file
        calendar_file_path = os.path.join(RESOURCES_PATH, calendar_filename)
        research_file_path = os.path.join(RESOURCES_PATH, f"research_consultant_{safe_topic}_{timestamp}.md")
        
        response_data = {
            "status": "success",
            "summary": str(result),
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
        
        return jsonify(response_data)
        
    except Exception as e:
        # Print full traceback for debugging
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        
        return jsonify({
            "status": "error", 
            "message": str(e),
            "traceback": traceback.format_exc(),
            "storage_info": {
                "storage_dir": STORAGE_DIR,
                "resources_path": RESOURCES_PATH
            }
        }), 500





@app.route('/calendar-only', methods=['POST'])
def get_calendar_only():
    """Return only the content calendar without summary"""
    try:
        # Get inputs and run crew
        data = request.get_json()
        
        if 'current_date' not in data:
            data['current_date'] = datetime.now().strftime("%Y-%m-%d")
        
        # Create topic-specific filename
        topic = data.get('topic', 'default_topic')
        safe_topic = sanitize_filename(topic)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        calendar_filename = f"content_calendar_{safe_topic}_{timestamp}.md"
        
        content_inputs = Content(**data)
        enhanced_inputs = content_inputs.dict()
        enhanced_inputs.update({
            'calendar_filename': calendar_filename,
            'safe_topic': safe_topic
        })
        
        crew_instance = TheConsultantCrew()
        crew_instance.consultantcrew().kickoff(inputs=enhanced_inputs)
        
        # Return only the calendar content from topic-specific file
        calendar_file_path = os.path.join(RESOURCES_PATH, calendar_filename)
        
        if os.path.exists(calendar_file_path):
            with open(calendar_file_path, 'r', encoding='utf-8') as file:
                calendar_content = file.read()
            
            return calendar_content, 200, {'Content-Type': 'text/markdown'}
        else:
            return jsonify({
                "status": "error",
                "message": f"Content calendar file not found: {calendar_filename}",
                "expected_path": calendar_file_path
            }), 404
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 400

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check with storage information"""
    return jsonify({
        "status": "healthy",
        "storage_info": {
            "storage_dir": STORAGE_DIR,
            "resources_path": RESOURCES_PATH,
            "storage_exists": os.path.exists(STORAGE_DIR),
            "resources_exists": os.path.exists(RESOURCES_PATH),
            "environment": os.environ.get("ENVIRONMENT", "development")
        }
    })



@app.route('/inputs', methods=['GET'])
def get_required_inputs():
    """Return required input schema"""
    return jsonify({
        "inputs": list(Content.__fields__.keys())
    })

if __name__ == "__main__":
    app.run(debug=True)