import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

'''
Python AWS Lambda function that takes in password, reason and timestamp and records all events. Response is NOT needed. Can be 204.

# Pseudocode
- First do a look up on users table to check if the record exists. If not throw error and exit.
- Take the request payload and simply make an entry in the DynamoDB table 'quiz_user_events' 

DynamoDB table 'quiz_user_events' sample record
{ "password": "12345","username": "John Doe","reason": "Window unfocused","timestamp": "2025-10-28T10:30:00.000Z"}

# Request and Response payloads are as follows. 
Request: Request: {  "password": "student_token",  "reason": "Window unfocused",  "timestamp": "2025-10-28T10:30:00.000Z"}
Response: None

# This function will be invoked by an API Gateway endpoint. 
'''

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'users'))
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE', 'quiz_user_events'))

def lambda_handler(event, context):
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
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        # Extract required fields
        password = body.get('password')
        reason = body.get('reason')
        timestamp = body.get('timestamp')
        
        # Validate required fields
        if not password or not reason or not timestamp:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Missing required fields: password, reason, or timestamp'})
            }
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid timestamp format. Use ISO 8601 format'})
            }
        
        username = None

        # Check if user exists in users table
        try:
            response = users_table.get_item(Key={'password': password})
            username = response.get('Item', {}).get('username')
            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'User not found'})
                }
        except Exception as e:
            print(f"Error checking user: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Error validating user'})
            }
        
        # Record event in quiz_user_events table
        try:
            events_table.put_item(
                Item={
                    'password': password,
                    'timestamp': timestamp,
                    'reason': reason,
                    'username': username
                }
            )
        except Exception as e:
            print(f"Error recording event: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Error recording event'})
            }
        
        # Return 204 No Content on success
        return {
            'statusCode': 204,
            'headers': {'Content-Type': 'application/json'}
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }