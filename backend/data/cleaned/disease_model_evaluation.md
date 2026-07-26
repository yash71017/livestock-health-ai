# Disease Classification Model — Evaluation Report

## Baseline (majority class)
Accuracy: 0.137

## Logistic Regression (class_weight=balanced)
Accuracy: 0.240
Classification Report:
                                    precision    recall  f1-score   support

                        Bluetongue       0.09      0.27      0.14        11
        Bovine Respiratory Disease       0.00      0.00      0.00        17
Bovine Respiratory Syncytial Virus       0.00      0.00      0.00         4
               Bovine Tuberculosis       0.27      0.25      0.26        16
             Bovine Viral Diarrhea       0.00      0.00      0.00         4
    Caprine Arthritis Encephalitis       0.56      0.53      0.55        17
           Caprine Pleuropneumonia       0.42      1.00      0.59         5
       Caprine Respiratory Disease       0.00      0.00      0.00         4
                       Coccidiosis       0.40      1.00      0.57         4
            Foot and Mouth Disease       0.00      0.00      0.00        10
                   Johne's Disease       0.43      0.33      0.38         9
                          Mastitis       0.57      0.57      0.57         7
                         Pneumonia       0.17      0.17      0.17         6
       Rare — Consult Veterinarian       0.50      0.05      0.09        20
                           Scrapie       0.05      0.08      0.06        12

                          accuracy                           0.24       146
                         macro avg       0.23      0.28      0.22       146
                      weighted avg       0.26      0.24      0.21       146


## Gradient Boosting
Accuracy: 0.247
Classification Report:
                                    precision    recall  f1-score   support

                        Bluetongue       0.00      0.00      0.00        11
        Bovine Respiratory Disease       0.14      0.29      0.19        17
Bovine Respiratory Syncytial Virus       0.00      0.00      0.00         4
               Bovine Tuberculosis       0.18      0.38      0.24        16
             Bovine Viral Diarrhea       0.00      0.00      0.00         4
    Caprine Arthritis Encephalitis       0.48      0.71      0.57        17
           Caprine Pleuropneumonia       0.38      0.60      0.46         5
       Caprine Respiratory Disease       0.00      0.00      0.00         4
                       Coccidiosis       0.33      0.50      0.40         4
            Foot and Mouth Disease       0.00      0.00      0.00        10
                   Johne's Disease       0.00      0.00      0.00         9
                          Mastitis       0.50      0.43      0.46         7
                         Pneumonia       0.00      0.00      0.00         6
       Rare — Consult Veterinarian       0.31      0.25      0.28        20
                           Scrapie       0.00      0.00      0.00        12

                          accuracy                           0.25       146
                         macro avg       0.15      0.21      0.17       146
                      weighted avg       0.18      0.25      0.20       146


## Final Model: LogisticRegression (calibrated)
Trained on 146 samples, 15 classes

## Feature Importances (symptom influence)
  Vomiting: 0.7418
  Coughing: 0.6272
  Loss of Appetite: 0.5748
  Fever: 0.5048
  Decreased Milk Yield: 0.4844
  Nasal Discharge: 0.4516
  Diarrhea: 0.4188
  Weight Loss: 0.3811
  Lethargy: 0.3547
  Dehydration: 0.3490
  Swollen Joints: 0.3388
  Labored Breathing: 0.3140
  Reduced Wool Production: 0.1545
  Swollen Legs: 0.1132
  Lameness: 0.0847
