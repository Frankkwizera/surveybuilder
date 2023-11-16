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
                response_dict = { "message": "Survey generated successfully"}
                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')
                
            except Exception as e:
                response_dict = {"error": str(e)}
                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
        else:
            return jsonify({"error": "Invalid file format. Please upload a JSON file."}), 400
    
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
                
            elif field_type == 'number':
                generated_survey.append({'question': field_name, 'type': 'number'})
                
            elif field_type == 'integer':
                min_value = field.get('min_value')
                max_value = field.get('max_value')
                generated_survey.append({'question': field_name, 'type': 'number', 'validation': {'min': min_value, 'max': max_value}})
                
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
        

api.add_resource(SurveyGenerator, '/surveys')
api.add_resource(SurveySimulator, '/simulate')

if __name__ == '__main__':
    app.run(debug=True)
