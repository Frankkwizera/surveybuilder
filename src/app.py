import sys
import os

# Assuming your current working directory is where the 'project' directory resides
project_path = os.path.abspath(os.path.join(os.getcwd(), "surveybuilder"))
sys.path.append(project_path)

from flask import Flask, request, jsonify, Response
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.dialects.postgresql import JSONB
import uuid
import http
import json
import hashlib

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://pindo_user:pindo_password@localhost/pindo_challenge'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
api = Api(app)

# Initialize the database
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# TODO(1): Move database modes to a different file
class UploadedFile(db.Model):
    __tablename__ = 'uploaded_files'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    json_dict = db.Column(JSONB)  # JSONB column for storing JSON data
    sha256_hash = db.Column(db.String(64), unique=True)
    # survey = db.relationship('Survey', backref='uploaded_file', uselist=False)
    
    def __repr__(self):
        return '<UploadedFile %r>' % self.sha256_hash


class Survey(db.Model):
    __tablename__ = 'surveys'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(100))
    file_id = db.Column(db.String(36))
    
    def __repr__(self):
        return '<Survey %r>' % self.title

# Global variables to store surveys and computed hashes
SURVEY_QUESTIONS = []
SURVEY_INDEX = 0
QUESTION_INDEX = 0


class SurveyGenerator(Resource):
    """
    Handles generation and storage of surveys.
    """

    def post(self):
        """
        Generates a survey from an uploaded JSON file.

        Returns:
            JSON response indicating successful survey generation or error messages.
        """
        
        uploaded_file = request.files['file']
        if uploaded_file.filename.endswith('.json'):
            try:
                json_file_content = uploaded_file.read()
                
                # Calculate the hash to detect duplicates
                sha256_hash = hashlib.sha256(json_file_content).hexdigest()
                existing_file = UploadedFile.query.filter_by(sha256_hash=sha256_hash).first()
                if existing_file:
                    response_dict = {"message": "JSON file is already uploaded."}
                    return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')

                survey_data = json.loads(json_file_content.decode('utf-8'))
                
                # Store the file content and its hash in the database
                file_data = UploadedFile(json_dict=survey_data, sha256_hash=sha256_hash)
                db.session.add(file_data)
                db.session.commit()
                
                # Generate a survey
                survey_title = survey_data.get('title', [])
                fields = survey_data.get('fields', [])
                survey_questions = self.generate_survey(fields)
                SURVEY_QUESTIONS.append({"title": survey_title, "questionaire": survey_questions})
                response_dict = { "message": f"{survey_title} survey generated successfully"}

                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')
                
            except Exception as e:
                response_dict = {"error": str(e)}
                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
        else:    
            return Response(response=json.dumps({"error": "Invalid file format. Please upload a JSON file."}), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
    
    def get(self, uuid = None):
        """
        Retrieves all surveys or a specific survey by UUID.

        Parameters:
            uuid: (Optional) Identifier for the specific survey.

        Returns:
            JSON response containing requested survey/s or error messages.
        """
        if uuid:
            uploaded_file = UploadedFile.query.get(uuid)
            if uploaded_file:
                survey_data = uploaded_file.json_dict
            
                survey_title = survey_data.get('title', [])
                fields = survey_data.get('fields', [])
                survey_questions = self.generate_survey(fields)
                
                single_survey_response_dict = {
                    'title': survey_title,
                    'questionaire': survey_questions,
                    'uuid': uploaded_file.id,
                    'sha256_hash': uploaded_file.sha256_hash
                }

                return Response(response=json.dumps(single_survey_response_dict), status=http.HTTPStatus.OK, mimetype='application/json')
                
            response_dict = {"message": "Survey does not exits."}
            return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
            
        uploaded_files = UploadedFile.query.all()
        files_data = []
        for uploaded_file in uploaded_files:
            survey_data = uploaded_file.json_dict
            
            survey_title = survey_data.get('title', [])
            fields = survey_data.get('fields', [])
            survey_questions = self.generate_survey(fields)
            
            files_data.append({
                'title': survey_title,
                'questionaire': survey_questions,
                'uuid': uploaded_file.id,
                'sha256_hash': uploaded_file.sha256_hash
            })
        return Response(response=json.dumps(files_data), status=http.HTTPStatus.OK, mimetype='application/json')

    @staticmethod
    def generate_survey(fields):
        """
        Generates survey questions based on provided field definitions.

        Parameters:
            fields: List of field definitions from the uploaded JSON file.

        Returns:
            List of generated survey questions.
        """

        generated_survey = []

        for field in fields:
            field_type = field.get('input_type')
            field_name = field.get('field_name')
            
            # Handle different input types to generate survey questions/forms
            if field_type == 'text':
                generated_survey.append({'question': field_name, 'type': 'text', 'validation': {'maxLength': field.get('expected_length')}})
                
            elif field_type == 'email':
                generated_survey.append({'question': field_name, 'type': 'email'})
                
            elif field_type == 'integer':
                min_value = field.get('min_value')
                max_value = field.get('max_value')
                generated_survey.append({'question': field_name, 'type': 'integer', 'validation': {'min': min_value, 'max': max_value}})
                
            elif field_type == 'multiple_choice':
                choices = field.get('choices', [])
                generated_survey.append({'question': field_name, 'type': 'multiple_choice', 'options': choices})
                
            elif field_type == 'textarea':
                generated_survey.append({'question': field_name, 'type': 'textarea', 'validation': {'maxLength': field.get('expected_length')}})
                
            # TODO: Handle other field types as needed

        return generated_survey

class SurveySimulator(Resource):
    """
    Simulates taking a survey by fetching and displaying questions sequentially.
    """

    def post(self):
        """
        Handles survey simulation.

        Returns:
            Response: JSON response containing the next survey question or completion message.
        """
        global QUESTION_INDEX
        global SURVEY_INDEX
        
        selected_survey_index = None
        json_data = request.json
        if json_data:
            survey_uuid = json_data.get('survey_uuid')
            survey_question_index = json_data.get('question_index', QUESTION_INDEX)
            survey_question_index = int(survey_question_index)

        selected_survey = uploaded_file = UploadedFile.query.get(survey_uuid)
        survey_data = uploaded_file.json_dict
        survey_title = survey_data.get('title', [])
        fields = survey_data.get('fields', [])
        survey_questions = SurveyGenerator.generate_survey(fields)
        
        if survey_question_index >= len(survey_questions):
            response_dict = {"message": f'{survey_title} survey is completed successfully.'}
            return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')
            
        current_question = survey_questions[survey_question_index]
        response_dict = {
            "title": survey_title,
            "question": f"{survey_question_index + 1}. " + current_question['question']
        }
        
        QUESTION_INDEX = survey_question_index + 1
        return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')
       
class SurveyResponseHandler(Resource):
    def post(self):
        """
        Handles answering a specific question in a survey.

        Expects JSON payload with
            - survey_uuid:
            - question_index: 
            - answer:
        """
        json_data = request.json

        survey_uuid = json_data.get('survey_uuid')
        question_index = json_data.get('question_index', None)
        answer = json_data.get('answer')
        
        if None in [survey_uuid, answer]:
            response_dict = {"message" : "Missing required parameters, survey_uuid and answer"}
            return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
        
        survey_index = int(survey_uuid)
        if question_index:
            question_index = int(question_index)
            if question_index < 0 or question_index >= len(SURVEY_QUESTIONS[survey_index]['questionaire']):
                response_dict = {"message": "Invalid question index"}
                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
           
        return self.validate_response(SURVEY_QUESTIONS[survey_index], question_index, answer)

    def validate_response(self, selected_survey, question_index, answer):
        """
        Validates user response for a specific question in a survey.

        Parameters:
            selected_survey: 
            question_index:
            answer:

        Returns:
            Response: JSON response indicating validation success or failure.
        """
        expected_questions = selected_survey['questionaire']
        question_index = question_index if question_index else 0
        question = expected_questions[question_index]
        
        response_dict = {
           "current_question": question,
           "answer": answer
        }
       
        # Integers
        if question['type'] == 'integer':
            if not isinstance(answer, int) or not (question['validation']['min'] <= answer <= question['validation']['max']):
                response_dict["is_response_valid"] = False
                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
        
        # Text & Textarea
        elif question['type'] == 'text' or question['type'] == 'textarea':
            if not isinstance(answer, str) or len(answer) > question['validation']['maxLength']:
                response_dict["is_response_valid"] = False
                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
        
        # Email
        elif question['type'] == 'email':
            # Basic email format validation using regex
            import re
            email_pattern = re.compile(r"[^@]+@[^@]+\.[^@]+")
            if not re.match(email_pattern, answer):
                response_dict["is_response_valid"] = False
                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
        
        # Multiple choice
        elif question['type'] == 'multiple_choice':
            # Check if the user's response is among the available choices
            choices = question.get('options', [])
            if answer not in choices:
                response_dict["is_response_valid"] = False
                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
        
        # If the response passes validation
        response_dict["is_response_valid"] = True
        
        # Progress to the next question
        next_question_index = question_index + 1
        if next_question_index < len(expected_questions):
            response_dict['next_question'] = {
                "question_index": next_question_index,
                "details": expected_questions[next_question_index]
            }
        return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')

api.add_resource(SurveyGenerator, '/surveys', '/surveys/<string:uuid>')
api.add_resource(SurveySimulator, '/simulate')
api.add_resource(SurveyResponseHandler, '/answer') 

if __name__ == '__main__':
    app.run(debug=True)
