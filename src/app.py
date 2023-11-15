from flask import Flask, request, jsonify, Response
from flask_restful import Resource, Api
import http
import json

app = Flask(__name__)
api = Api(app)

global SURVEY_QUESTIONS
SURVEY_QUESTIONS = []

global CURRENT_SURVEY_INDEX
global CURRENT_QUESTION_INDEX
CURRENT_SURVEY_INDEX = 0
CURRENT_QUESTION_INDEX = 0


class SurveyGenerator(Resource):
    def post(self):
        uploaded_file = request.files['file']
        if uploaded_file.filename.endswith('.json'):
            # TODO: Hash the json file to easily catch duplicates
            try:
                json_data = uploaded_file.read().decode('utf-8')
                survey_data = json.loads(json_data)
                
                # Generate a survey
                survey_title = survey_data.get('title', [])
                fields = survey_data.get('fields', [])
                survey_questions = self.generate_survey(fields)
                SURVEY_QUESTIONS.append({"title": survey_title, "questionaire": survey_questions})
                response_dict = { "message": "Survey generated successfully"}
                return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')
                
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        else:
            return jsonify({"error": "Invalid file format. Please upload a JSON file."}), 400
    
    def get(self, survey_uuid = None):
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
    def post(self):
        # Logic to simulate the survey
        global CURRENT_QUESTION_INDEX
        selected_survey = SURVEY_QUESTIONS[CURRENT_SURVEY_INDEX]
        if CURRENT_QUESTION_INDEX >= len(selected_survey['questionaire']):
            response_dict = {"message": "Survey completed successfully."}
            return Response(response=json.dumps(response_dict), status=http.HTTPStatus.BAD_REQUEST, mimetype='application/json')
            
        current_question = selected_survey['questionaire'][CURRENT_QUESTION_INDEX]
        
        response_dict = {
            "survey_title": selected_survey['title'],
            "question": current_question['question']
        }
        
        CURRENT_QUESTION_INDEX += 1
        return Response(response=json.dumps(response_dict), status=http.HTTPStatus.OK, mimetype='application/json')
    
    
api.add_resource(SurveyGenerator, '/surveys')
api.add_resource(SurveySimulator, '/simulate')

if __name__ == '__main__':
    app.run(debug=True)
