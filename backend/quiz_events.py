import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'users'))
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE', 'quiz_user_events'))

CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'POST,OPTIONS'
}

def respond(status, payload):
    return {
        'statusCode': status,
        'headers': CORS_HEADERS,
        'body': json.dumps(payload)
    }

def lambda_handler(event, context):
    # Preflight
    if event.get('httpMethod') == 'OPTIONS':
        return respond(200, {'message': 'CORS preflight successful'})

    try:
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        password = body.get('password')
        reason = body.get('reason')
        timestamp = body.get('timestamp')

        if not password or not reason or not timestamp:
            return respond(400, {'error': 'Missing required fields: password, reason, or timestamp'})

        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            return respond(400, {'error': 'Invalid timestamp format. Use ISO 8601 format'})

        try:
            response = users_table.get_item(Key={'password': password})
            if 'Item' not in response:
                return respond(404, {'error': 'User not found'})
            username = response['Item'].get('username')
        except Exception as e:
            print(f"Error checking user: {str(e)}")
            return respond(500, {'error': 'Error validating user'})

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
            return respond(500, {'error': 'Error recording event'})

        return respond(200, {'message': 'Event recorded successfully'})

    except json.JSONDecodeError:
        return respond(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return respond(500, {'error': 'Internal server error'})