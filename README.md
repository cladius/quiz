# Quiz Application

A full-stack quiz application built with React.js frontend and AWS Lambda backend, designed for secure online assessments with cheating detection and automated scoring.

## Features

- **User Authentication**: Password-based login system
- **Dynamic Quiz Loading**: Questions fetched from DynamoDB based on user credentials
- **Question Shuffling**: Randomizes question order for each user
- **Timer Functionality**: Configurable time limits with automatic submission
- **Cheating Detection**: Logs window focus changes, tab switches, and minimization attempts
- **Multiple Choice Support**: Handles both single and multiple-choice questions
- **Real-time Progress**: Question navigator with visual indicators
- **Automated Scoring**: Server-side score calculation with partial credit handling
- **Email Reports**: Generates and sends detailed quiz reports via email
- **Session Persistence**: Saves progress in browser session storage
- **Responsive Design**: Bootstrap-based UI that works on desktop and mobile

## Tech Stack

### Frontend

- **React.js** (v19.2.0) - UI framework
- **Bootstrap** (v5.3.0) - CSS framework
- **Lucide React** - Icon library
- **Web Vitals** - Performance monitoring
- **Session Storage** - Client-side state persistence

### Backend

- **AWS Lambda** - Serverless functions (Python 3.x)
- **API Gateway** - REST API endpoints
- **DynamoDB** - NoSQL database
- **Zoho Mail** - Email service for reports
- **Boto3** - AWS SDK for Python

### Infrastructure

- **AWS Amplify** - Frontend hosting and deployment
- **AWS CloudFormation** - Infrastructure as Code (implied)

## Architecture

```
Frontend (React) <-> API Gateway <-> Lambda Functions <-> DynamoDB
     |                    |                    |
  Amplify            Endpoints:           Tables:
- Login/Auth        - /authenticate      - users
- Quiz UI           - /questions         - questions
- Timer/Events      - /submit            - quiz_user_events
- Results           - /alert
- Reports           - /analyze
```

## Database Schema

### Users Table

```json
{
  "password": "string (primary key)",
  "username": "string",
  "quiz_id": "string",
  "answers": "map (optional)",
  "marks": "number (optional)",
  "is_submitted": "boolean (optional)",
  "email": "string (optional)",
  "resubmission_attempts": "list (optional)"
}
```

### Questions Table

```json
{
  "quiz_id": "string (partition key)",
  "order": "number (sort key)",
  "question": "string",
  "options": "list",
  "correct_options": "string (comma-separated indices)",
  "marks": "number",
  "multiple_choice": "boolean"
}
```

### Quiz User Events Table

```json
{
  "password": "string (partition key)",
  "timestamp": "string (sort key)",
  "reason": "string",
  "username": "string"
}
```

## API Endpoints

### POST /authenticate

Authenticates user and returns username/quiz_id.

```json
Request: {"password": "string"}
Response: {"username": "string", "quiz_id": "string"}
```

### POST /questions

Fetches quiz questions for authenticated user.

```json
Request: {"quiz_id": "string", "password": "string"}
Response: {"questions": [...]}
```

### POST /submit

Submits quiz answers and calculates score.

```json
Request: {"password": "string", "answers": {"q1": 0, "q2": [0,1]}}
Response: {"score": 85}
```

### POST /alert

Logs cheating detection events.

```json
Request: {"password": "string", "reason": "string", "timestamp": "ISO string"}
Response: 204 No Content
```

### POST /analyze

Generates and emails detailed quiz report.

```json
Request: {"password": "string"}
Response: {"report": "string", "username": "string", ...}
```

## Setup & Installation

### Prerequisites

- Node.js (v16+)
- npm or yarn
- AWS CLI configured
- Python 3.x (for Lambda development)

### Frontend Setup

```bash
cd frontend
npm install
npm start  # Development server on localhost:3000
npm run build  # Production build
```

### Backend Setup

1. Deploy Lambda functions to AWS
2. Configure API Gateway endpoints
3. Set up DynamoDB tables
4. Configure environment variables:
   - `ZOHO_EMAIL`
   - `ZOHO_PASSWORD`
   - `ZOHO_SMTP_HOST`
   - `ZOHO_SMTP_PORT`
   - `DYNAMODB_TABLE`
   - `USERS_TABLE`
   - `EVENTS_TABLE`

### Deployment

- **Frontend**: Deploy to AWS Amplify via Git integration
- **Backend**: Deploy Lambda functions via AWS Console, CLI, or CloudFormation

## Usage

1. **Login**: Enter password to authenticate
2. **Instructions**: Review quiz rules and time limit
3. **Quiz**: Answer questions with timer running
4. **Navigation**: Use question navigator or next/previous buttons
5. **Submit**: Click "Submit Test" or wait for auto-submission
6. **Results**: View score and logout

## Security Features

- Password-based authentication
- Session storage for state persistence
- Cheating detection via focus/blur events
- Event logging for audit trails
- CORS enabled for cross-origin requests
- Input validation on all endpoints

## Development

### Frontend Scripts

- `npm start` - Start development server
- [`npm test`](frontend/src/App.test.js) - Run test suite
- `npm run build` - Create production build
- `npm run eject` - Eject from Create React App

### Testing

```bash
cd frontend
npm test
```

### Code Quality

- ESLint configuration included
- React Testing Library for component tests
- Jest for unit testing

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## License

This project is proprietary. All rights reserved.
