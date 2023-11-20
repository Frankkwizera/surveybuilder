import io
import pytest
from src.app import app as flask_app

@pytest.fixture
def client():
    with flask_app.test_client() as client:
        yield client
        
JSON_FILE_CONTENT = b"{\"title\":\"List of Cars\",\"fields\":[{\"field_name\":\"Maker\",\"input_type\":\"text\",\"expected_length\":50},{\"field_name\":\"Year\",\"input_type\":\"integer\",\"min_value\":1970,\"max_value\":2023},{\"field_name\":\"Hybrid\",\"input_type\":\"multiple_choice\",\"choices\":[\"Yes\",\"No\"]}]}"

class TestSurveyBuilder:
    @pytest.mark.parametrize("file_name, expected_status, expected_message", [
        ('valid_survey.json', 200, b'survey generated successfully'),
        ('invalid_format.txt', 400, b'Invalid file format'),
    ])
    def test_survey_generator(self, client, file_name, expected_status, expected_message):
        # Create a fake file-like object
        file_content = None
        if file_name == "valid_survey.json":
            # file_content = b'{"fake": "data"}'
            file_content = JSON_FILE_CONTENT
        else:
            file_content = b'{"fake": "data"}'
        fake_file = io.BytesIO(file_content)
        fake_file.name = file_name

        data = {'file': (fake_file, file_name)}
        response = client.post('/surveys', data=data, content_type='multipart/form-data')
        assert response.status_code == expected_status
        assert expected_message in response.data

    def test_survey_simulator(self, client):
        pass
        
    def test_survey_response_handler(self, client):
        pass