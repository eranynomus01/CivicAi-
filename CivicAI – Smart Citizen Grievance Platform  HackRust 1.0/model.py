# model.py
import joblib
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

class ComplaintClassifier:
    """
    Wrapper class for the complaint classification model
    """
    
    def __init__(self, model_path='models/complaint_classifier.pkl'):
        self.model_path = model_path
        self.model = None
        self.categories = [
            'Roads',
            'Electricity', 
            'Water',
            'Waste Management',
            'Public Safety'
        ]
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or create a new one if it doesn't exist"""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print("Model loaded successfully")
            except Exception as e:
                print(f"Error loading model: {e}")
                self.create_new_model()
        else:
            print("Model not found. Creating new model...")
            self.create_new_model()
    
    def create_new_model(self):
        """Create a new model with basic training data"""
        # Import here to avoid circular imports
        from train_model import train_classifier
        self.model = train_classifier()
    
    def predict(self, text):
        """
        Predict category for a complaint
        
        Args:
            text: Complaint text (title + description)
            
        Returns:
            tuple: (category, confidence_score)
        """
        if not self.model:
            return "Uncategorized", 0.0
        
        try:
            # Make prediction
            prediction = self.model.predict([text])[0]
            
            # Get confidence score (probability)
            probabilities = self.model.predict_proba([text])[0]
            confidence = max(probabilities)
            
            return prediction, float(confidence)
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return "Uncategorized", 0.0
    
    def predict_batch(self, texts):
        """Predict categories for multiple complaints"""
        predictions = []
        for text in texts:
            category, confidence = self.predict(text)
            predictions.append({
                'category': category,
                'confidence': confidence
            })
        return predictions
    
    def get_department(self, category):
        """
        Get the department responsible for a category
        
        Args:
            category: Complaint category
            
        Returns:
            str: Department name
        """
        department_mapping = {
            'Roads': 'Department of Transportation',
            'Electricity': 'Power Distribution Company',
            'Water': 'Water and Sewerage Authority',
            'Waste Management': 'Sanitation Department',
            'Public Safety': 'Police Department',
            'Uncategorized': 'General Services Department'
        }
        
        return department_mapping.get(category, 'General Services Department')

# Create global classifier instance - THIS IS WHAT app.py IS TRYING TO IMPORT
classifier = ComplaintClassifier()