from flask import Flask, request, jsonify, Response
from flask_restful import Resource, Api
import http
import json
import hashlib

app = Flask(__name__)
api = Api(app)

# Global variables to store surveys and computed hashes
COMPUTED_HASHES = []
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
                
                if sha256_hash in COMPUTED_HASHES:
                    response_dict = {"message": "JSON file is already uploaded."}
                    return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
                    
                COMPUTED_HASHES.append(sha256_hash)
                survey_data = json.loads(json_file_content.decode('utf-8'))
                
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
    
    def get(self, survey_uuid = None):
        """
        Retrieves all surveys or a specific survey by UUID.

        Parameters:
            survey_uuid: (Optional) Identifier for the specific survey.

        Returns:
            JSON response containing requested survey/s or error messages.
        """

        if survey_uuid:
            # TODO: Implement a database client to query from
            survey_index = int(survey_uuid)
            if not survey_index or survey_index > len(SURVEY_QUESTIONS):
                response_dict = {"message": "Survey does not exits."}
                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
                
            single_survey_response_dict = SURVEY_QUESTIONS[survey_index]
            return Response(response=json.dumps(single_survey_response_dict), status=http.HTTPStatus.OK, mimetype='application/json')
            
        response_dict = SURVEY_QUESTIONS
        return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')

    def generate_survey(self, fields):
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
            selected_survey_index = int(survey_uuid)
            
        # Rest question index if the survey is changed
        current_survey_index = selected_survey_index if selected_survey_index is not None else SURVEY_INDEX
        if current_survey_index != SURVEY_INDEX:
            SURVEY_INDEX = current_survey_index
            QUESTION_INDEX = 0

        selected_survey = SURVEY_QUESTIONS[current_survey_index]
        survey_title = selected_survey['title']
        if QUESTION_INDEX >= len(selected_survey['questionaire']):
            response_dict = {"message": f'{survey_title} survey is completed successfully.'}
            return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')
            
        current_question = selected_survey['questionaire'][QUESTION_INDEX]
        
        response_dict = {
            "title": survey_title,
            "question": f"{QUESTION_INDEX + 1}. " + current_question['question']
        }
        
        QUESTION_INDEX += 1
        return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')
    
    def validate_response(self):
        """
        Validates user responses (to be implemented).
        """
        pass
       
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
        question_index = json_data.get('question_index')
        answer = json_data.get('answer')
        
        if None in [survey_uuid, question_index, answer]:
            response_dict = {"message" : "Missing required parameters, survey_uuid, question_index and answer"}
            return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
        
        survey_index = int(survey_uuid)
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
        question = expected_questions[question_index]
        
        response_dict = {
           "question": question,
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
        return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')

api.add_resource(SurveyGenerator, '/surveys')
api.add_resource(SurveySimulator, '/simulate')
api.add_resource(SurveyResponseHandler, '/answer') 

if __name__ == '__main__':
    app.run(debug=True)
