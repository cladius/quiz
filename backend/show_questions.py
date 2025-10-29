import json
import boto3
import os
from boto3.dynamodb.conditions import Key
from decimal import Decimal

'''
This AWS Lambda function takes a quiz_id and password and provides the questions
# DynamoDB table 'questions' contains user information like this
{
 "quiz_id": "final",
 "order": 0,
 "correct_option": 2,
 "marks": 1,
 "multiple_choice": false,
 "options": [
  "Fad",
  "Technology",
  "Application of GenAI",
  "FOMO Course"
 ],
 "question": "What is Agentic AI?"
}

# This function will be invoked by an API Gateway endpoint.
# The quiz_id is the partition key for the DynamoDB table. and order is the sort key

# Request and Response payloads are as follows.

Request: { 
  "quiz_id": "final",
  "password": "12345"
}

Response: {
  "questions": [
    {
      "order": 1,
      "question": "What is 2+2?",
      "options": ["2", "3", "4", "5"],
      "marks": 1
    }
  ]
}
'''

# Custom JSON encoder to handle Decimal types from DynamoDB
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'questions')
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    """
    Lambda function to retrieve quiz questions from DynamoDB.
    Expects quiz_id and password in the request body.
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
        # Log the incoming event for debugging
        print(f"Received event: {json.dumps(event)}")
        
        # Parse the request body from API Gateway
        if 'body' in event and isinstance(event['body'], str):
            body = json.loads(event['body'])
        elif 'body' in event:
            body = event['body']
        else:
            # Direct Lambda invocation (not through API Gateway)
            body = event
        
        print(f"Parsed body: {json.dumps(body)}")
        
        # Extract quiz_id and password from request
        quiz_id = body.get('quiz_id')
        password = body.get('password')
        
        # Validate required fields
        if not quiz_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'quiz_id is required'})
            }
        
        if not password:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'password is required'})
            }
        
        print(f"Querying DynamoDB for quiz_id: {quiz_id}")
        
        # Query DynamoDB for all questions with the given quiz_id
        response = table.query(
            KeyConditionExpression=Key('quiz_id').eq(quiz_id)
        )
        
        print(f"DynamoDB response: {json.dumps(response, cls=DecimalEncoder)}")
        
        items = response.get('Items', [])
        
        if not items:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Quiz not found'})
            }
        
        # Format questions for response (exclude sensitive data like correct_option)
        questions = []
        for item in sorted(items, key=lambda x: int(x.get('order', 0))):
            questions.append({
                'id': "q" + str(int(item.get('order', 0))),
                'order': int(item.get('order', 0)),
                'question': str(item.get('question', '')),
                'options': item.get('options', []),
                'marks': int(item.get('marks', 1)),
                'multiple_choice': bool(item.get('multiple_choice', False))
            })
        
        print(f"Formatted questions: {json.dumps(questions)}")
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'questions': questions}, cls=DecimalEncoder)
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'Invalid JSON in request body: {str(e)}'})
        }
    
    except Exception as e:
        # Log the full error for debugging
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e),
                'type': type(e).__name__
            })
        }