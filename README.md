# Pedagogical AI

An educational platform powered by artificial intelligence to enhance learning experiences.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine.

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository** (if you haven't already)
   ```bash
   git clone <repository-url>
   cd pedagogical_ai
   ```

2. **Create a virtual environment**
   ```bash
   # On Windows
   python -m venv venv
   
   # Activate the virtual environment
   # On Windows
   venv\Scripts\activate
   ```

3. **Install the required packages**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Copy the `.env.example` file to `.env` and update the values:
   ```bash
   cp .env.example .env
   ```
   
   Edit the `.env` file and replace the placeholder values with your actual configuration:
   - `SECRET_KEY`: Generate a random secret key for security
   - `DATABASE_URL`: Database connection string (default is SQLite)
   - `GEMINI_API_KEY`: Your Google Gemini API key (optional for now)

5. **Initialize the database** (if needed)
   ```bash
   # This step might be needed in future versions when models are added
   ```

### Running the Application

To start the development server:

```bash
python run.py
```

The application will be available at `http://localhost:5000`

### Development

#### Project Structure
```
pedagogical_ai/
├── app/              # Main application package
│   ├── routes/       # URL routing
│   ├── models/       # Database models
│   ├── services/     # Business logic
│   ├── ai/           # AI integration components
│   └── utils/        # Utility functions
├── templates/        # HTML templates
├── static/           # Static files (CSS, JS, images)
├── uploads/          # User uploaded files
├── exports/          # Exported content
├── config.py         # Configuration settings
├── run.py            # Application entry point
├── requirements.txt  # Python dependencies
├── .env.example     # Environment variables template
├── .gitignore        # Git ignore rules
└── README.md         # This file
```

### Features

This initial version provides:
- Basic Flask application structure
- Dashboard page with responsive sidebar navigation
- Template inheritance with base layout
- Static file serving (CSS, JavaScript)
- Environment-based configuration
- Error handling (404, 500)

Future features will include:
- Course management system
- AI-powered exercise generation
- Interactive quizzes
- Learning analytics
- Document processing
- And much more...

### Contributing

Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests.

### License

This project is licensed under the MIT License - see the LICENSE file for details.

### Acknowledgments

- Built with Flask web framework
- Styled with Bootstrap 5
- Database management with SQLAlchemy