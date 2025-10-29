import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import smtplib
import os
from email.mime.text import MIMEText

def send_email(to_address, subject, body):
    # Read credentials from Lambda environment variables
    zoho_email = os.environ.get('ZOHO_EMAIL')
    zoho_password = os.environ.get('ZOHO_PASSWORD')
    zoho_smtp_host = os.environ.get('ZOHO_SMTP_HOST', 'smtp.zoho.com')
    zoho_smtp_port = int(os.environ.get('ZOHO_SMTP_PORT', '465'))
    
    # Validate required credentials are present
    if not zoho_email or not zoho_password:
        raise ValueError("ZOHO_EMAIL and ZOHO_PASSWORD environment variables must be set")
    
    print(f"Sending email to: {to_address}\nSubject: {subject}\nBody:\n{body}\n")
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = zoho_email
    msg['To'] = to_address

    with smtplib.SMTP_SSL(zoho_smtp_host, zoho_smtp_port) as server:
        server.login(zoho_email, zoho_password)
        server.send_message(msg)
    
    print(f"Email sent successfully to {to_address}")

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
        email = user.get('email', None)
        
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
            
            # Check if answered correctly
            is_correct = False
            if user_answer is not None:
                if isinstance(user_answer, list):
                    # For multiple choice, check if sets match
                    user_answer_set = set(user_answer)
                    correct_options_set = set(correct_options)
                    is_correct = user_answer_set == correct_options_set
                else:
                    # For single choice, check if answer matches
                    is_correct = user_answer in correct_options
            
            # Display result
            if is_correct:
                report_lines.append("Result: ✓ Answered Correctly")
            else:
                report_lines.append("Result: ✗ Answered Incorrectly")
            
            # Show marks for this question
            report_lines.append(f"Marks: {question_marks}")
            report_lines.append("")
        
        report_lines.append("=" * 80)
        report_lines.append(f"Your Score: {marks}/{total_possible_marks}")
        
        report_text = "\n".join(report_lines)

        # Step 5: Send report via email if email is available
        if email:
            email_subject = f"Quiz Report for {username} (Quiz ID: {quiz_id})"
            send_email(email, email_subject, report_text)
        
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