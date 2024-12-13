from flask import Flask, render_template, request, jsonify
import requests
import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Weather Prediction Function
def predict_weather(mean_temp, mean_precip):
    threshold_drought_temp = 30
    threshold_flood_precip = 50
    threshold_rainy_precip = 5

    prediction = "Normal Weather Conditions"

    if mean_temp is not None and mean_temp > threshold_drought_temp and mean_precip <= threshold_flood_precip:
        prediction = "Drought"
    elif mean_temp is not None and mean_temp < threshold_drought_temp and mean_precip > threshold_flood_precip:
        prediction = "Flood"
    elif mean_precip > threshold_flood_precip:
        prediction = "Heavy Rain/Flood"
    elif mean_precip > threshold_rainy_precip:
        prediction = "Rainy"
    elif mean_temp > 25 and mean_precip == 0:
        prediction = "Sunny"
    elif mean_temp < 15 and mean_precip == 0:
        prediction = "Cold and Clear"
    elif mean_precip == 0 and mean_temp >= 15 and mean_temp <= 25:
        prediction = "Normal Weather"
    elif mean_precip == 0 and mean_temp > 30:
        prediction = "Hot and Dry"

    return round(mean_temp, 2), round(mean_precip, 2), prediction

# Fetch Weather Data
def fetch_weather_data(api_key, city):
    url = f'http://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&appid={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        forecasts = data.get('list', [])

        daily_forecasts = []
        today = datetime.datetime.now().date()
        for i in range(7):
            forecast_date = today + datetime.timedelta(days=i)
            day_forecast = next((f for f in forecasts if datetime.datetime.fromtimestamp(f['dt']).date() == forecast_date), None)
            if day_forecast:
                temperature = day_forecast['main']['temp']
                precipitation = day_forecast.get('rain', {}).get('3h', 0)
                daily_forecasts.append({
                    "date": forecast_date.strftime('%Y-%m-%d'),
                    "predicted_temperature": temperature,
                    "predicted_precipitation": precipitation
                })
        return daily_forecasts
    return None

# Get the Gemini API URL and API Key from environment variables
gemini_api_url = os.getenv("GEMINI_API_URL")
gemini_api_key = os.getenv("GEMINI_API_KEY")

def get_gemini_response(query, api_key):
    """Fetch the response from Gemini API."""
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": query
                    }
                ]
            }
        ]
    }
    params = {
        "key": api_key
    }
    try:
        # Sending a POST request to the Gemini API
        response = requests.post(gemini_api_url, json=payload, headers=headers, params=params)
        response.raise_for_status()  

        # Extracting the chatbot response from the API
        data = response.json()
        candidates = data.get("candidates", [{}])
        if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
            return candidates[0]["content"]["parts"][0].get("text", "I couldn't fetch a response from Gemini.")
        return "No valid response from Gemini."
    except requests.exceptions.RequestException as e:
        # Handle connection errors or invalid responses
        return f"Error connecting to Gemini API: {e}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/weather', methods=['POST'])
def weather():
    city = request.form.get('city')
    # Get the Weather API Key from environment variables
    weather_api_key = os.getenv("WEATHER_API_KEY")
    
    daily_forecasts = fetch_weather_data(weather_api_key, city)
    if daily_forecasts:
        mean_temp = sum([day['predicted_temperature'] for day in daily_forecasts]) / len(daily_forecasts)
        mean_precip = sum([day['predicted_precipitation'] for day in daily_forecasts]) / len(daily_forecasts)
        temp, precip, prediction = predict_weather(mean_temp, mean_precip)
        return jsonify({
            "city": city,
            "prediction": prediction,
            "daily_forecasts": daily_forecasts
        })
    return jsonify({"error": "Unable to fetch weather data."})

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form.get('message')
    chatbot_response = get_gemini_response(user_input, gemini_api_key)
    return jsonify({"response": chatbot_response})

if __name__ == '__main__':
    app.run(debug=True)
