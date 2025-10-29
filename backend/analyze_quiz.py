import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

'''
Python AWS Lambda function that takes in input as password and generates a detailed quiz report for that person

# Pseudocode
- First do a look up on users table to check if the record exists. If not throw error and exit.
- Then get the answers attribute
- Then get the quiz_id and lookup the questions from questions table
- Then prepare a detailed report like this

Q1: ....
Options: 1, 2, 3, 4 (Note:in code it starts from 0, but on UI start with 1)
Your selection: 1
Actual correct answer(s): 2

# DB details

DynamoDB table 'users' sample record
{
 "password": "123",
 "answers": {
  "q2": [
   2,
   1
  ],
  "q5": 1
 },
 "is_submitted": true,
 "marks": 2,
 "quiz_id": "final",
"username": "Sameer"}

DynamoDB table 'questions' contains user information like this
The quiz_id is the partition key for the DynamoDB table. and order is the sort key
{ "quiz_id": "final", "order": 2, "correct_options": "1,2", "marks": 2, "multiple_choice": true, "options": [  "Fad",  "LLM + Tools",  "Fundamental aspect of Agentic AI",  "FOMO" ], "question": "What is an Agent?"}
{ "quiz_id": "final", "order": 5, "correct_options": "2", "marks": 1, "multiple_choice": false, "options": [  "Fad",  "A question",  "Application of GenAI",  "FOMO Course" ], "question": "What is Agentic AI?"}

Expected input:
{
  "password": "367"
}
'''

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('users')
questions_table = dynamodb.Table('questions')


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to int/float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    """
    AWS Lambda handler to generate detailed quiz report
    
    Expected input:
    {
        "password": "123"
    }
    """
    try:
        # Parse input
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        password = body.get('password')
        
        if not password:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Password is required'})
            }
        
        # Step 1: Look up user by password
        response = users_table.scan(
            FilterExpression='password = :pwd',
            ExpressionAttributeValues={':pwd': password}
        )
        
        if not response['Items'] or len(response['Items']) == 0:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'User not found with the provided password'})
            }
        
        user = response['Items'][0]
        
        # Step 2: Get user's answers
        answers = user.get('answers', {})
        quiz_id = user.get('quiz_id')
        username = user.get('username', 'Unknown')
        marks = user.get('marks', 0)
        is_submitted = user.get('is_submitted', False)
        
        if not quiz_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Quiz ID not found for this user'})
            }
        
        # Step 3: Get all questions for the quiz
        questions_response = questions_table.query(
            KeyConditionExpression=Key('quiz_id').eq(quiz_id)
        )
        
        questions = sorted(questions_response['Items'], key=lambda x: x['order'])
        
        if not questions:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': f'No questions found for quiz_id: {quiz_id}'})
            }
        
        # Step 4: Prepare detailed report
        report_lines = []
        report_lines.append(f"Quiz Report for: {username}")
        report_lines.append(f"Quiz ID: {quiz_id}")
        report_lines.append(f"Total Marks: {marks}")
        report_lines.append(f"Submitted: {'Yes' if is_submitted else 'No'}")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        total_possible_marks = 0
        
        for idx, q in enumerate(questions, 1):
            question_key = f"q{q['order']}"
            user_answer = answers.get(question_key, None)
            
            # Parse correct answers
            correct_options_str = str(q['correct_options'])
            correct_options = [int(x.strip()) for x in correct_options_str.split(',')]
            
            is_multiple_choice = q.get('multiple_choice', False)
            question_marks = q.get('marks', 0)
            total_possible_marks += question_marks
            
            # Format question
            report_lines.append(f"Q{idx}: {q['question']}")
            
            # Format options (starting from 1 for display)
            options_list = q.get('options', [])
            report_lines.append("Options:")
            for opt_idx, option in enumerate(options_list, 1):
                report_lines.append(f"  {opt_idx}. {option}")
            
            # Format user's selection
            if user_answer is not None:
                if isinstance(user_answer, list):
                    # Convert from 0-indexed to 1-indexed for display
                    displayed_answers = [a + 1 for a in user_answer]
                    report_lines.append(f"Your selection: {', '.join(map(str, displayed_answers))}")
                else:
                    # Single answer - convert from 0-indexed to 1-indexed
                    displayed_answer = user_answer + 1
                    report_lines.append(f"Your selection: {displayed_answer}")
            else:
                report_lines.append("Your selection: Not answered")
            
            # Format correct answer(s) - convert from 0-indexed to 1-indexed
            correct_displayed = [c + 1 for c in correct_options]
            if len(correct_displayed) > 1:
                report_lines.append(f"Actual correct answer(s): {', '.join(map(str, correct_displayed))}")
            else:
                report_lines.append(f"Actual correct answer(s): {correct_displayed[0]}")
            
            # Show marks for this question
            report_lines.append(f"Marks: {question_marks}")
            report_lines.append("")
        
        report_lines.append("=" * 80)
        report_lines.append(f"Your Score: {marks}/{total_possible_marks}")
        
        report_text = "\n".join(report_lines)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'report': report_text,
                'username': username,
                'quiz_id': quiz_id,
                'marks': marks,
                'total_marks': total_possible_marks,
                'is_submitted': is_submitted
            }, cls=DecimalEncoder),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }