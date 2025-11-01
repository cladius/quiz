import React, { useState, useEffect } from 'react';

const API_BASE_URL = 'https://dz8xd5aucf.execute-api.ap-south-1.amazonaws.com/prod';

export default function QuizApplication() {
  const [currentView, setCurrentView] = useState('login');
  const [password, setPassword] = useState('');
  const [user, setUser] = useState(() => {
    // Load saved user from storage on initial mount
    const savedUser = window.sessionStorage.getItem('quizUser');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [questions, setQuestions] = useState(() => {
    // Load saved questions from storage on initial mount
    const savedQuestions = window.sessionStorage.getItem('quizQuestions');
    return savedQuestions ? JSON.parse(savedQuestions) : [];
  });
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(() => {
    // Load saved question index from storage
    const savedIndex = window.sessionStorage.getItem('quizCurrentIndex');
    return savedIndex ? parseInt(savedIndex) : 0;
  });
  const [answers, setAnswers] = useState(() => {
    // Load saved answers from storage on initial mount
    const savedAnswers = window.sessionStorage.getItem('quizAnswers');
    return savedAnswers ? JSON.parse(savedAnswers) : {};
  });
  const [timeRemaining, setTimeRemaining] = useState(() => {
    // Load saved time from storage on initial mount
    const savedTime = window.sessionStorage.getItem('quizTimeRemaining');
    return savedTime ? parseInt(savedTime) : null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState(() => {
    // Load submitted state from storage
    const savedSubmitted = window.sessionStorage.getItem('quizSubmitted');
    return savedSubmitted === 'true';
  });

  // Initialize view based on saved state
  useEffect(() => {
    if (user && questions.length > 0) {
      const savedView = window.sessionStorage.getItem('quizCurrentView');
      if (savedView && savedView !== 'login') {
        setCurrentView(savedView);
      } else {
        setCurrentView('instructions');
      }
    }
  }, []);

  // Save user to storage whenever it changes
  useEffect(() => {
    if (user) {
      window.sessionStorage.setItem('quizUser', JSON.stringify(user));
    } else {
      window.sessionStorage.removeItem('quizUser');
    }
  }, [user]);

  // Save questions to storage whenever they change
  useEffect(() => {
    if (questions.length > 0) {
      window.sessionStorage.setItem('quizQuestions', JSON.stringify(questions));
    } else {
      window.sessionStorage.removeItem('quizQuestions');
    }
  }, [questions]);

  // Save current view to storage
  useEffect(() => {
    window.sessionStorage.setItem('quizCurrentView', currentView);
  }, [currentView]);

  // Save current question index to storage
  useEffect(() => {
    window.sessionStorage.setItem('quizCurrentIndex', currentQuestionIndex.toString());
  }, [currentQuestionIndex]);

  // Save submitted state to storage
  useEffect(() => {
    window.sessionStorage.setItem('quizSubmitted', submitted.toString());
  }, [submitted]);

  // Load Bootstrap CSS
  useEffect(() => {
    const link = document.createElement('link');
    link.href = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    return () => {
      document.head.removeChild(link);
    };
  }, []);

  // Shuffle questions (Fisher-Yates algorithm)
  const shuffleQuestions = (questionsArray) => {
    const shuffled = [...questionsArray];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  };

  // Track window focus for cheating detection
  useEffect(() => {
    if (currentView === 'quiz' && user) {
      const handleBlur = () => {
        logAlert('Window unfocused');
      };

      const handleVisibilityChange = () => {
        if (document.hidden) {
          logAlert('Tab switched or minimized');
        }
      };

      window.addEventListener('blur', handleBlur);
      document.addEventListener('visibilitychange', handleVisibilityChange);

      return () => {
        window.removeEventListener('blur', handleBlur);
        document.removeEventListener('visibilitychange', handleVisibilityChange);
      };
    }
  }, [currentView, user]);

  // Timer countdown
  useEffect(() => {
    if (currentView === 'quiz' && timeRemaining > 0) {
      const timer = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            handleSubmit();
            return 0;
          }
          const newTime = prev - 1;
          // Save time to storage
          window.sessionStorage.setItem('quizTimeRemaining', newTime.toString());
          return newTime;
        });
      }, 1000);

      return () => clearInterval(timer);
    }
  }, [currentView, timeRemaining]);

  const logAlert = async (reason) => {
    try {
      await fetch(`${API_BASE_URL}/alert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          password: user.password,
          reason: reason,
          timestamp: new Date().toISOString()
        })
      });
    } catch (err) {
      console.error('Failed to log alert:', err);
    }
  };

  const handleLogin = async (e) => {
    if (e) e.preventDefault();
    if (!password) return;
    
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/authenticate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });

      if (!response.ok) {
        throw new Error('Invalid password');
      }

      const data = await response.json();
      setUser({ ...data, password });
      
      const questionsResponse = await fetch(`${API_BASE_URL}/questions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          quiz_id: data.quiz_id,
          password: password
        })
      });

      if (!questionsResponse.ok) {
        throw new Error('Failed to fetch questions');
      }

      const questionsData = await questionsResponse.json();
      const shuffledQuestions = shuffleQuestions(questionsData.questions);
      setQuestions(shuffledQuestions);
      setTimeRemaining(questionsData.duration || 7200);
      setCurrentView('instructions');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const startQuiz = () => {
    setCurrentView('quiz');
  };

  const handleAnswerSelect = (questionId, optionIndex) => {
    setAnswers(prev => {
      const question = questions.find(q => q.id === questionId);
      let newAnswer;

      if (question.multiple_choice) {
        // Ensure we have an array for multiple choice questions
        const currentAnswers = Array.isArray(prev[questionId]) ? prev[questionId] : [];
        
        if (currentAnswers.includes(optionIndex)) {
          newAnswer = currentAnswers.filter(i => i !== optionIndex);
        } else {
          newAnswer = [...currentAnswers, optionIndex];
        }
      } else {
        // For single choice, just set the option
        newAnswer = optionIndex;
      }

      const newAnswers = {
        ...prev,
        [questionId]: newAnswer
      };
      window.sessionStorage.setItem('quizAnswers', JSON.stringify(newAnswers));
      return newAnswers;
    });
  };

  const calculateScore = () => {
    let totalScore = 0;
    questions.forEach(question => {
      if (answers[question.id] === question.correct_option) {
        totalScore += question.marks;
      }
    });
    return totalScore;
  };

  const handleSubmit = async () => {
    if (submitted) return;
    
    setLoading(true);
    setSubmitted(true);

    try {
      const response = await fetch(`${API_BASE_URL}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          password: user.password,
          answers: answers
        })
      });

      if (!response.ok) {
        let errBody = null;
        try {
          errBody = await response.json();
        } catch (e) {
          // ignore parse errors
        }
        const msg = errBody?.error || errBody?.message || `Failed to submit answers (${response.status})`;
        throw new Error(msg);
      }

      const result = await response.json();
      setUser(prev => ({ ...prev, score: result.score }));
      setError(''); 
      setCurrentView('completed');
    } catch (err) {
      setError(err.message);
      setSubmitted(false);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    // clear saved state/storage and return to login
    window.sessionStorage.removeItem('quizAnswers');
    window.sessionStorage.removeItem('quizTimeRemaining');
    window.sessionStorage.removeItem('quizUser');
    window.sessionStorage.removeItem('quizQuestions');
    window.sessionStorage.removeItem('quizCurrentView');
    window.sessionStorage.removeItem('quizCurrentIndex');
    window.sessionStorage.removeItem('quizSubmitted');
    
    setPassword('');
    setUser(null);
    setQuestions([]);
    setCurrentQuestionIndex(0);
    setAnswers({});
    setTimeRemaining(null);
    setLoading(false);
    setError('');
    setSubmitted(false);
    setCurrentView('login');
  };
  
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Login View
  if (currentView === 'login') {
    return (
      <div className="min-vh-100 bg-light d-flex align-items-center justify-content-center p-4">
        <div className="card shadow-lg" style={{ maxWidth: '500px', width: '100%' }}>
          <div className="card-body p-5">
            <div className="text-center mb-4">
              <div className="bg-primary text-white rounded-circle d-inline-flex align-items-center justify-content-center mb-3" 
                   style={{ width: '64px', height: '64px' }}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </div>
              <h1 className="display-5 fw-bold mb-2">Quiz</h1>
              <p className="text-muted">Enter your password to begin</p>
            </div>

            <div className="mb-4">
              <label className="form-label fw-semibold">Password</label>
              <input
                type="password"
                className="form-control form-control-lg"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleLogin(e)}
                placeholder="Enter your password"
              />
            </div>

            {error && (
              <div className="alert alert-danger d-flex align-items-center mb-4" role="alert">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="me-2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={handleLogin}
              disabled={loading || !password}
              className="btn btn-primary btn-lg w-100"
            >
              {loading ? 'Authenticating...' : 'Login'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Instructions View
  if (currentView === 'instructions') {
    return (
      <div className="min-vh-100 bg-light d-flex align-items-center justify-content-center p-4">
        <div className="card shadow-lg" style={{ maxWidth: '800px', width: '100%' }}>
          <div className="card-body p-5">
            <h2 className="mb-4">Welcome, {user.username}!</h2>
            
            <div className="alert alert-warning mb-4">
              <h5 className="alert-heading fw-semibold mb-3">Important Instructions:</h5>
              <ul className="mb-0">
                <li>Total Questions: {questions.length}</li>
                <li>Time Limit: {formatTime(timeRemaining)}</li>
                <li>There is NO negative marking</li>
                <li>DO NOT switch tabs or minimize the window</li>
                <li>ALL such attempts will be logged silently</li>
                <li>Any such attempt will result in disqualification and lead to ZERO marks</li>
                <li>You can review and change answers before submitting</li>
                <li>Once the timer runs out, it will automatically submit your answers</li>
                <li>Click "Submit Test" when you're done</li>
                <li>Single choice questions have radio button options</li>
                <li>Multiple choice questions have checkbox options</li>
                <li>All the best!</li>
              </ul>
            </div>

            <div className="d-flex gap-3">
              <button
                onClick={startQuiz}
                className="btn btn-primary btn-lg flex-grow-1"
              >
                Start Quiz
              </button>
              <button
                onClick={handleLogout}
                className="btn btn-outline-secondary btn-lg"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Quiz View
  if (currentView === 'quiz') {
    const currentQuestion = questions[currentQuestionIndex];
    const progress = ((currentQuestionIndex + 1) / questions.length) * 100;

    return (
      <div className="min-vh-100 bg-light">
        {/* Header */}
        <div className="bg-white shadow-sm sticky-top">
          <div className="container py-3">
            <div className="d-flex justify-content-between align-items-center">
              <div>
                <h5 className="mb-1 fw-bold">{user.username}</h5>
                <small className="text-muted">Question {currentQuestionIndex + 1} of {questions.length}</small>
              </div>
              <div className="d-flex align-items-center gap-4">
                <button
                  onClick={handleLogout}
                  className="btn btn-outline-secondary btn-sm"
                >
                  Logout
                </button>
                <div className="d-flex align-items-center gap-2">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                  </svg>
                  <span className="fw-semibold fs-5">{formatTime(timeRemaining)}</span>
                </div>
              </div>
            </div>
          </div>
          <div className="progress" style={{ height: '4px' }}>
            <div 
              className="progress-bar bg-primary" 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        {/* Question Content */}
        <div className="container py-4">
          <div className="card shadow-sm mb-4">
            <div className="card-body p-4">
              <div className="mb-4">
                <span className="badge bg-primary rounded-pill px-3 py-2">
                  {currentQuestion.marks} {currentQuestion.marks === 1 ? 'Mark' : 'Marks'}
                </span>
              </div>
              
              <h4 className="mb-4 fw-semibold">
                {currentQuestion.question}
              </h4>

              <div className="d-grid gap-3">
                {currentQuestion.options.map((option, index) => {
                  const currentAnswer = answers[currentQuestion.id];
                  const isSelected = currentQuestion.multiple_choice 
                    ? (Array.isArray(currentAnswer) && currentAnswer.includes(index))
                    : (currentAnswer === index);

                  return (
                    <button
                      key={index}
                      onClick={() => handleAnswerSelect(currentQuestion.id, index)}
                      className={`btn btn-lg text-start p-3 ${
                        isSelected ? 'btn-primary' : 'btn-outline-secondary'
                      }`}
                    >
                      <div className="d-flex align-items-center gap-3">
                        {/* Radio button or checkbox container */}
                        <div 
                          className={`border border-2 d-flex align-items-center justify-content-center ${currentQuestion.multiple_choice ? 'rounded' : 'rounded-circle'}`}
                          style={{ 
                            width: '24px', 
                            height: '24px', 
                            minWidth: '24px'
                          }}
                        >
                          {isSelected && (
                            currentQuestion.multiple_choice ? (
                              // Checkmark for multiple choice
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                              </svg>
                            ) : (
                              // Filled circle for radio button
                              <div 
                                className="bg-white" 
                                style={{ 
                                  width: '12px', 
                                  height: '12px',
                                  borderRadius: '50%'
                                }}
                              ></div>
                            )
                          )}
                        </div>
                        <span>{option}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Show submission/API error (e.g. "Quiz already submitted") */}
          {error && (
            <div className="alert alert-danger d-flex align-items-center mb-4" role="alert">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="me-2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* Navigation */}
          <div className="d-flex gap-3 mb-4">
            <button
              onClick={() => setCurrentQuestionIndex(prev => Math.max(0, prev - 1))}
              disabled={currentQuestionIndex === 0}
              className="btn btn-outline-secondary btn-lg px-4"
            >
              Previous
            </button>
            
            {currentQuestionIndex < questions.length - 1 ? (
              <button
                onClick={() => setCurrentQuestionIndex(prev => prev + 1)}
                className="btn btn-primary btn-lg flex-grow-1"
              >
                Next Question
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={loading || submitted}
                className="btn btn-success btn-lg flex-grow-1"
              >
                {loading ? 'Submitting...' : 'Submit Test'}
              </button>
            )}
          </div>

          {/* Question Navigator */}
          <div className="card shadow-sm">
            <div className="card-body p-4">
              <h5 className="fw-semibold mb-3">Question Navigator</h5>
              <div className="d-flex flex-wrap gap-2 mb-3">
                {questions.map((q, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentQuestionIndex(index)}
                    className={`btn ${
                      answers[q.id] !== undefined
                        ? 'btn-success'
                        : index === currentQuestionIndex
                        ? 'btn-primary'
                        : 'btn-outline-secondary'
                    }`}
                    style={{ width: '48px', height: '48px' }}
                  >
                    {index + 1}
                  </button>
                ))}
              </div>
              <div className="d-flex gap-4 small">
                <div className="d-flex align-items-center gap-2">
                  <div className="bg-success" style={{ width: '16px', height: '16px' }}></div>
                  <span>Answered</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  <div className="bg-primary" style={{ width: '16px', height: '16px' }}></div>
                  <span>Current</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  <div className="border border-secondary" style={{ width: '16px', height: '16px' }}></div>
                  <span>Not Answered</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Completed View
  if (currentView === 'completed') {
    const totalMarks = questions.reduce((sum, q) => sum + q.marks, 0);
    
    return (
      <div className="min-vh-100 bg-light d-flex align-items-center justify-content-center p-4">
        <div className="card shadow-lg text-center" style={{ maxWidth: '500px', width: '100%' }}>
          <div className="card-body p-5">
            <div className="bg-success text-white rounded-circle d-inline-flex align-items-center justify-content-center mb-4" 
                 style={{ width: '80px', height: '80px' }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
            
            <h2 className="display-6 fw-bold mb-3">Test Submitted!</h2>
            <p className="text-muted mb-4">
              Thank you for completing the quiz, {user.username}.
            </p>

            {user.score !== undefined && (
              <div className="alert alert-primary mb-4">
                <p className="text-muted mb-2">Your Score</p>
                <p className="display-4 fw-bold mb-2 text-primary">
                  {user.score} / {totalMarks}
                </p>
                <p className="text-muted">
                  {Math.round((user.score / totalMarks) * 100)}%
                </p>
              </div>
            )}

            <div className="d-flex gap-3 justify-content-center">
              <button onClick={handleLogout} className="btn btn-outline-secondary">
                Logout
              </button>
            </div>
  
          </div>
        </div>
      </div>
    );
  }

  return null;
}