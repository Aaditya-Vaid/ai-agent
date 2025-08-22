# AI-Powered Personal Assistant
This project is a conversational AI agent designed to assist users with everyday tasks by integrating with various web services. Built on Python, the assistant uses the Google Gemini API's function-calling capabilities to interact with APIs for managing emails and fetching weather information.

## 🚀 Features
**Conversational AI**: Interacts with users in natural language to understand and fulfill requests.

**Email Management**:
  - Send new emails.
  - Create and manage drafts (add, update, and list drafts).
  - Weather Information: Fetch real-time weather and air quality index (AQI) data for any location.

**Robust Function Calling**: The model intelligently determines the appropriate tool (send_email, add_draft, get_weather, etc.) to call based on the user's query.

**Secure Authentication**: Handles user authentication with Google APIs using OAuth 2.0.

**Resilient Design**: Implements a robust error-handling mechanism with retries to ensure the application is reliable and handles API failures gracefully.

## 🛠️ Technologies Used
**Python 3.12**

**Google Gemini API**: For conversational AI and function calling.

**Google APIs Client Library for Python (google-api-python-client)**: For interacting with Gmail and People APIs.

**OAuth 2.0 for Python (google-auth-oauthlib)**: For secure user authentication.

```requests```: For making HTTP requests to the WeatherAPI.

```tenacity```: For implementing retry logic on API calls.

```pydantic```: For data validation.

```dotenv```: For managing environment variables.

## ⚙️ Getting Started
Follow these steps to set up and run the project locally.

### Prerequisites
Make sure you have Python 3.12 installed on your system.

### Installation
Clone this repository to your local machine.

Navigate to the project directory.

Install the required dependencies using pip:
```
pip install -r requirements.txt
```

### API Key and Credentials Setup
Google Gemini API: 

Obtain an API key from the Google AI Studio.

Create a ```.env``` file in the project root and add your key:
```
GEMINI_API_KEY=YOUR_API_KEY
```

Gmail API:

Follow the instructions in the Google Gmail API documentation to enable the API and download your ```credentials.json``` file.

Place the ```credentials.json``` file in the project's root directory.

WeatherAPI:

Sign up for a free API key at WeatherAPI.com.

Add your WeatherAPI key to the ```.env``` file:
```
WEATHER_API_KEY=YOUR_WEATHER_API_KEY
```
### Running the Application
Once everything is set up, you can run the agent from the command line:
```
python main.py
```
The agent will then prompt you to begin a conversation.

## 📂 Project Structure
```main.py```: Contains the core logic for the conversational agent, including tool declarations and the main conversational loop.

```tools.py```: Houses the functions that interact with external APIs (get_weather, add_draft, send_email, etc.).

```auth.py```: Handles the OAuth 2.0 authorization flow for Google APIs.

```.env```: Stores your API keys and sensitive information.

## ✨ Future Enhancements
**Calendar Integration**: Add tools to create, view, and manage calendar events.

**Task Management**: Allow users to create and track to-do lists.

**Personalization**: Enhance the assistant's ability to learn user preferences over time.

**Voice Interface**: Integrate a speech-to-text and text-to-speech service to enable voice conversations.
