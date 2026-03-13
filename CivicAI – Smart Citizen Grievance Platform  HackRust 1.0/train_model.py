# train_model.py
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
import joblib
import os

def train_classifier():
    """
    Train a Naive Bayes classifier to categorize complaints
    """
    print("Training complaint classification model...")
    
    # Sample training data - in production, this would come from historical complaints
    training_data = [
        # Roads category
        ("Pothole on Main Street needs repair", "Roads"),
        ("Road damage causing traffic", "Roads"),
        ("Street light not working on Highway", "Roads"),
        ("Manhole cover missing on sidewalk", "Roads"),
        ("Road construction causing dust", "Roads"),
        ("Deep pothole on residential street", "Roads"),
        ("Road needs repaving", "Roads"),
        ("Missing road signs", "Roads"),
        ("Poor road condition", "Roads"),
        
        # Electricity category
        ("Power outage in downtown area", "Electricity"),
        ("Street light not working", "Electricity"),
        ("Electrical pole leaning dangerously", "Electricity"),
        ("High voltage wire hanging low", "Electricity"),
        ("Transformer explosion heard", "Electricity"),
        ("Frequent power cuts", "Electricity"),
        ("Voltage fluctuations", "Electricity"),
        
        # Water category
        ("Water pipeline burst on Elm Street", "Water"),
        ("No water supply since morning", "Water"),
        ("Dirty water coming from tap", "Water"),
        ("Water pressure too low", "Water"),
        ("Sewage water overflowing", "Water"),
        ("Leaking water pipe", "Water"),
        ("Water contamination", "Water"),
        
        # Waste Management category
        ("Garbage not collected for a week", "Waste Management"),
        ("Illegal dumping in empty lot", "Waste Management"),
        ("Overflowing trash bins", "Waste Management"),
        ("Stray animals spreading garbage", "Waste Management"),
        ("Recycling not picked up", "Waste Management"),
        ("Bad smell from garbage", "Waste Management"),
        
        # Public Safety category
        ("Abandoned vehicle on street", "Public Safety"),
        ("Suspicious activity in park", "Public Safety"),
        ("Broken streetlight creating dark area", "Public Safety"),
        ("Speeding vehicles in school zone", "Public Safety"),
        ("Graffiti on public building", "Public Safety"),
        ("Unsafe sidewalk", "Public Safety"),
    ]
    
    # Create DataFrame
    df = pd.DataFrame(training_data, columns=['text', 'category'])
    
    # Features and labels
    X = df['text']
    y = df['category']
    
    # Create pipeline with TF-IDF and Naive Bayes
    model = make_pipeline(
        TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),  # Use both unigrams and bigrams
            max_features=5000
        ),
        MultinomialNB(alpha=0.1)  # Laplace smoothing
    )
    
    # Train the model
    model.fit(X, y)
    
    # Test the model
    test_complaints = [
        "Deep pothole on residential street needs immediate repair",
        "No electricity for 3 hours in our neighborhood",
        "Water leaking from main pipe for 2 days",
        "Garbage truck didn't come this week",
        "Man with weapon seen near school"
    ]
    
    print("\nTesting model with sample complaints:")
    for complaint in test_complaints:
        pred = model.predict([complaint])[0]
        proba = model.predict_proba([complaint]).max()
        print(f"Complaint: {complaint[:50]}...")
        print(f"Predicted: {pred} (confidence: {proba:.2f})\n")
    
    # Save the model
    if not os.path.exists('models'):
        os.makedirs('models')
    
    model_path = 'models/complaint_classifier.pkl'
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")
    
    return model

if __name__ == "__main__":
    train_classifier()