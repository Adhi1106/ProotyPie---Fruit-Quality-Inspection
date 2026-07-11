# ProotyPie

## Overview

ProotyPie is an AI-powered fruit quality inspection system that combines deep learning and generative AI to assist users in identifying fruits, evaluating their freshness, and receiving intelligent storage recommendations.

The application uses a TensorFlow model to classify the freshness of supported fruits while Google Gemini enhances the system by recognizing unsupported fruits, validating uploaded images, generating storage recommendations, and answering fruit-related queries through an integrated AI assistant.

The objective of this project is to reduce food wastage by helping users make informed decisions about fruit quality and storage.

---

## Problem Statement

Determining whether a fruit is safe to consume is often based on visual judgement, which can be inaccurate. Existing solutions generally focus only on classification and do not provide practical guidance regarding storage, shelf life, or nutritional information.

ProotyPie addresses this limitation by combining computer vision with generative AI to create a more informative and interactive fruit quality assessment system.

---

## Features

- Freshness classification for Apple, Banana, and Orange using TensorFlow.
- Identification of unsupported fruits using Google Gemini.
- Detection of non-fruit images with appropriate user feedback.
- AI-generated storage recommendations.
- Shelf-life estimation based on fruit type and freshness.
- Temperature and humidity recommendations.
- Nutrition highlights and fruit facts.
- AI chatbot for fruit-related questions.
- Modern web interface built using Next.js.

---

## Technology Stack

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

### Backend

- Python
- FastAPI

### Artificial Intelligence

- TensorFlow
- MobileNetV2
- Google Gemini API

### Supporting Libraries

- NumPy
- Pillow
- python-dotenv
- Google GenAI SDK

---

## System Workflow

1. The user uploads an image through the web interface.
2. Google Gemini validates whether the uploaded image contains a fruit.
3. If the fruit belongs to the supported dataset, the TensorFlow model predicts its freshness.
4. Gemini generates storage recommendations, shelf-life information, nutrition highlights, and practical advice.
5. Users can further interact with the AI assistant to ask fruit-related questions.

---

## Supported Fruits

The TensorFlow model currently supports quality classification for:

- Apple
- Banana
- Orange

If another fruit is uploaded, Gemini identifies it and provides useful storage recommendations. Since the TensorFlow model has not been trained on that fruit, freshness prediction is not performed.

---

## Project Structure

```
ProotyPie
│
├── api/
├── backend/
├── frontend/
├── docs/
├── models/
├── README.md
└── .gitignore
```

---

## Installation

### Clone the repository

```bash
git clone https://github.com/your-username/prootypie.git
```

### Navigate to the project

```bash
cd prootypie
```

### Create a virtual environment

```bash
python -m venv .venv
```

### Activate the virtual environment

Windows

```bash
.venv\Scripts\activate
```

macOS/Linux

```bash
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure the Gemini API

Create a `.env` file in the project directory.

```
GEMINI_API_KEY=YOUR_API_KEY
```

### Run the backend

```bash
uvicorn api.server:app --reload
```

### Run the frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Future Enhancements

- Support for additional fruit varieties.
- Fruit disease detection.
- Freshness prediction for a larger dataset.
- Voice-enabled AI assistant.
- Mobile application.
- Cloud deployment.
- Barcode and QR code integration for packaged produce.

---

## Learning Outcomes

This project provided practical experience in:

- Deep learning for image classification.
- TensorFlow model development and deployment.
- Integration of large language models through the Gemini API.
- Building REST APIs using FastAPI.
- Developing responsive web applications with Next.js.
- Secure API key management using environment variables.
- Full-stack AI application development.
- Version control using Git and GitHub.

---

## Authors

Adhira Praveen

Bachelor of Technology  
Artificial Intelligence and Machine Learning

---

## License

This project was developed for academic purposes.
