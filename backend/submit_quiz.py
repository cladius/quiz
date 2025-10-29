import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('users')
questions_table = dynamodb.Table('questions')

'''
This is a Python AWS Lambda function takes a password and answer selection and submits the quiz on behalf of the user.

# Pseudocode
- First do a look up on users table based on password to determine quiz_id
- Take the request payload and simply update the user's record - set/overwrite the answers portion to the answers attribute of the user's record
- Do a read on questions table to get all the questions based on quiz_id.
- Iterate over the request payload's "answers" dict.
- In the request payload the question id would be "q2", "q3", etc. Remove "q" to obtain the numerical order.
- Based on this order match, check if the answers submitted by the user match the correct_options mentioned for the question. 
- Note: that for multiple_choice true questions, there can be more than 1 correct option. The order of options selected by the user DOES NOT matter. So handle this.
- Start the user's score as 0.
- Keep incrementing the score for each exactly correct question according to the marks mentioned for that question. Meaning if user has provided 1 correct option out of 2 - do NOT give marks.
- After going through all the questions, add the marks attritbute in the user's column
- Also set the is_submitted flag to True
- Before processing of this function, check for above flag and if it's True, throw an error.

DynamoDB table 'users' sample record
{ "password": "12345","quiz_id": "final","username": "Auxilin"}

DynamoDB table 'questions' contains user information like this
The quiz_id is the partition key for the DynamoDB table. and order is the sort key
{ "quiz_id": "final", "order": 2, "correct_options": "1,2", "marks": 2, "multiple_choice": true, "options": [  "Fad",  "LLM + Tools",  "Fundamental aspect of Agentic AI",  "FOMO" ], "question": "What is an Agent?"}
{ "quiz_id": "final", "order": 5, "correct_options": "2", "marks": 1, "multiple_choice": false, "options": [  "Fad",  "A question",  "Application of GenAI",  "FOMO Course" ], "question": "What is Agentic AI?"}

# Request and Response payloads are as follows. 
Request: {"password":"12345","answers":{"q2":[1,2],"q5":2}}
Response: {"score": 85}

This function will be invoked by an API Gateway endpoint.
'''


def lambda_handler(event, context):
    """
    Lambda function to submit quiz answers and calculate score
    """
    # CORS headers
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }
    
    # Handle OPTIONS preflight request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'CORS preflight successful'})
        }
    
    try:
        # Parse request body from API Gateway
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        password = body.get('password')
        answers = body.get('answers', {})
        
        if not password:
            return create_response(400, {'error': 'Password is required'})
        
        if not answers:
            return create_response(400, {'error': 'Answers are required'})
        
        # Look up user by password
        user_response = users_table.scan(
            FilterExpression='password = :pwd',
            ExpressionAttributeValues={':pwd': password}
        )
        
        if not user_response.get('Items'):
            return create_response(404, {'error': 'User not found'})
        
        user = user_response['Items'][0]
        user_password = user['password']
        quiz_id = user['quiz_id']
        
        # Check if quiz already submitted
        if user.get('is_submitted', False):
            # Quiz already submitted BUT let's record this re-submission attempt in a separate attribute 
            # of the same user record for auditing purposes
            users_table.update_item(
                Key={'password': user_password},
                UpdateExpression='SET resubmission_attempts = list_append(if_not_exists(resubmission_attempts, :empty_list), :attempt)',
                ExpressionAttributeValues={
                    ':attempt': [answers],
                    ':empty_list': []
                }
            )

            # Return error response
            return create_response(400, {'error': 'Quiz already submitted'})
        
        # Update user's answers first
        users_table.update_item(
            Key={'password': user_password},
            UpdateExpression='SET answers = :ans',
            ExpressionAttributeValues={':ans': answers}
        )
        
        # Fetch all questions for this quiz
        questions_response = questions_table.query(
            KeyConditionExpression=Key('quiz_id').eq(quiz_id)
        )
        
        questions = questions_response.get('Items', [])
        
        if not questions:
            return create_response(404, {'error': 'No questions found for this quiz'})
        
        # Calculate score
        score = 0
        
        for question in questions:
            order = int(question['order'])
            question_key = f"q{order}"
            
            # Check if user answered this question
            if question_key not in answers:
                continue
            
            user_answer = answers[question_key]
            correct_options = question['correct_options']
            marks = int(question['marks']) if isinstance(question['marks'], (int, Decimal)) else int(question['marks'])
            is_multiple_choice = question.get('multiple_choice', False)
            
            # Parse correct options
            if isinstance(correct_options, str):
                correct_set = set(map(int, correct_options.split(',')))
            else:
                correct_set = {int(correct_options)}
            
            # Parse user answer
            if isinstance(user_answer, list):
                user_set = set(user_answer)
            else:
                user_set = {user_answer}
            
            # Check if answer is exactly correct
            if user_set == correct_set:
                score += marks
        
        # Update user record with score and submission flag
        users_table.update_item(
            Key={'password': user_password},
            UpdateExpression='SET marks = :score, is_submitted = :submitted',
            ExpressionAttributeValues={
                ':score': score,
                ':submitted': True
            }
        )
        
        return create_response(200, {'score': score})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})


def create_response(status_code, body):
    """
    Create API Gateway response
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }