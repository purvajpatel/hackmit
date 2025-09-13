# ResearchConnect - AI-Powered Research Labs Connection Platform

A modern web application that connects students with research laboratories at universities using AI-powered recommendations and transcript analysis. This application was inspired by the HackAI project but features a completely different UI and enhanced functionality.

## Features

- **Modern UI**: Clean, responsive design with smooth animations and gradients
- **Lab Discovery**: Browse through 200+ research labs with detailed information
- **Smart Filtering**: Search by lab name, professor, school, or keywords
- **AI-Powered Analysis**: Upload your transcript and get personalized recommendations using OpenAI
- **Drag & Drop Upload**: Easy transcript upload with drag-and-drop functionality
- **Personalized Recommendations**: Get AI-powered lab suggestions based on your major and interests
- **Interactive Modal**: Detailed lab information in an elegant modal interface
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **AI Integration**: OpenAI GPT API with file search capabilities
- **Data**: JSON-based lab database
- **Styling**: Custom CSS with modern design patterns
- **Icons**: Font Awesome
- **Fonts**: Inter (Google Fonts)

## Installation

1. Clone or download this repository
2. Navigate to the project directory:
   ```bash
   cd research_labs_app
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

5. Run the application:
   ```bash
   python app.py
   ```

6. Open your browser and visit `http://localhost:5000`

## Usage

### Exploring Labs
- Use the search bar to find labs by name, professor, or keywords
- Filter labs by school using the dropdown
- Click on any lab card to view detailed information
- Use the "Load More" button to see additional labs

### AI-Powered Analysis
1. Navigate to the "AI Analysis" section
2. Fill in your student information (name, major, GPA, year)
3. Select your career goals and research interests
4. Optionally upload your transcript by dragging and dropping a PDF file
5. Click "Get AI Recommendations" to receive personalized analysis
6. View comprehensive recommendations based on your profile and transcript

### Getting Basic Recommendations
1. Navigate to the "Get Matched" section
2. Enter your major (e.g., "Computer Science", "Biology")
3. Select your research interests from the available options
4. Click "Find My Perfect Labs" to get personalized recommendations
5. View the recommended labs with relevance scores

### Lab Details
- Click on any lab card or "View Details" button
- View comprehensive information including:
  - Lab name and description
  - Professor information
  - School affiliation
  - Lab website link
  - Contact options

## AI Features

### Transcript Analysis
- Upload your academic transcript (PDF format)
- AI analyzes your coursework and grades
- Provides personalized recommendations based on academic performance
- Suggests research areas that align with your strengths

### Intelligent Matching
- Uses OpenAI's GPT models for sophisticated analysis
- Considers multiple factors: major, interests, academic performance, goals
- Provides detailed explanations for recommendations
- Suggests specific labs and research directions

### RAG (Retrieval Augmented Generation)
- Combines lab database with AI analysis
- Provides context-aware recommendations
- References specific labs and professors
- Offers actionable advice for research opportunities

## Data Structure

The application uses a JSON database (`data/utd_all_labs.json`) containing information about research labs including:
- Lab name
- Professor name
- School affiliation
- Lab website URL
- Detailed description

## API Endpoints

- `GET /` - Main application page
- `GET /api/labs` - Get all labs (with optional filtering)
- `GET /api/schools` - Get all unique schools
- `GET /api/lab/<id>` - Get specific lab details
- `POST /api/recommendations` - Get basic personalized recommendations
- `POST /api/ai-recommendations` - Get AI-powered recommendations with transcript analysis

## Configuration

### OpenAI Setup
1. Get an API key from [OpenAI](https://platform.openai.com/api-keys)
2. Add it to your `.env` file
3. Optionally, create a custom assistant for more specialized recommendations

### File Upload
- Maximum file size: 10MB
- Supported format: PDF
- Files are temporarily stored during processing and then deleted

## Customization

### Adding New Labs
Edit the `data/utd_all_labs.json` file to add new research labs. Each lab should follow this structure:
```json
{
    "name": "Lab Name",
    "professor": "Professor Name",
    "url": "https://lab-website.com",
    "school": "School Name",
    "description": "Detailed lab description..."
}
```

### Styling
Modify `static/css/style.css` to customize the appearance:
- Colors and gradients
- Typography
- Layout and spacing
- Animations and transitions

### Functionality
Extend `static/js/script.js` to add new features:
- Additional filtering options
- Enhanced search capabilities
- New recommendation algorithms
- Additional lab information

## Browser Support

- Chrome (recommended)
- Firefox
- Safari
- Edge

## Security Notes

- API keys are stored in environment variables
- Uploaded files are temporarily stored and automatically deleted
- No persistent storage of user data
- All AI processing is done server-side

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Inspired by the HackAI project
- Lab data sourced from university research databases
- UI design inspired by modern web design trends
- AI integration powered by OpenAI's GPT models
