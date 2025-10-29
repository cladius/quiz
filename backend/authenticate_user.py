# This AWS Lambda function takes a password and provides the username and quiz_id as response.
# DynamoDB table 'users' contains user information like this
# { "password": "12345", "quiz_id": "final", "username": "Auxilin" }
# This function will be invoked by an API Gateway endpoint.
# The password is the partition key for the DynamoDB table.
# The request body will be as follows
# Request: { "password": "student_token" }
# And Response: { "username": "John Doe", "quiz_id": "quiz_123"}

import json
import boto3
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('users')

def lambda_handler(event, context):
    """
    Lambda function to retrieve username and quiz_id based on password.
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
        # Parse the request body from API Gateway
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract password from request
        password = body.get('password')
        
        if not password:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': 'Password is required'
                })
            }
        
        # Query DynamoDB table using password as partition key
        response = table.get_item(
            Key={
                'password': password
            }
        )
        
        # Check if item exists
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': 'Invalid password'
                })
            }
        
        # Extract user data
        item = response['Item']
        username = item.get('username')
        quiz_id = item.get('quiz_id')
        
        # Return successful response
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'username': username,
                'quiz_id': quiz_id
            })
        }
        
    except ClientError as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': f'Database error: {str(e)}'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({
                'error': 'Invalid JSON in request body'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }