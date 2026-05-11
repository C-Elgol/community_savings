# Smart Community Savings & Loan Management System

An intelligent community savings, cooperative, and Njangi management platform designed to digitize savings operations, automate loan management, and provide AI-powered credit risk analysis and loan decision support.

---

## 📌 Project Overview

This system was developed to modernize traditional community savings and cooperative financial systems by integrating:

- Digital savings management
- Loan lifecycle management
- Intelligent credit scoring
- Probability of Default (PD) prediction
- Role-based access control
- Financial analytics and reporting
- Community governance tools

The platform helps savings groups and cooperatives improve transparency, accountability, loan monitoring, and financial decision-making.

---

# 🚀 Key Features

## 👥 Member Management
- Member registration and profile management
- Role and permission management
- Group participation tracking
- Attendance monitoring

---

## 💰 Savings Management
- Contribution tracking
- Savings history
- Automated balance calculations
- Savings stability analysis
- Share-out calculations

---

## 🏦 Loan Management
- Loan application workflow
- Loan approval system
- Repayment scheduling
- Penalty management
- Loan status monitoring
- Loan history tracking

---

## 🧠 AI-Powered Credit Risk Analysis
The system integrates behavioral financial analytics and machine learning techniques to evaluate member reliability and predict loan default risk.

### Behavioral Indicators Used
- Contribution consistency
- Repayment punctuality
- Default history
- Attendance score
- Savings stability
- Loan-to-savings ratio
- Overdue repayment behavior
- Current unpaid loans

---

## 📊 Credit Scoring Engine

The platform computes member creditworthiness using weighted behavioral scoring:

\[
CS=(w_1C+w_2R+w_3(1-D)+w_4A+w_5S)\times100
\]

Where:
- \(C\) = Contribution Consistency
- \(R\) = Repayment Punctuality
- \(D\) = Default History
- \(A\) = Attendance Score
- \(S\) = Savings Stability

---

## 📈 Probability of Default Prediction

The system uses Logistic Regression to estimate the likelihood that a member may default on a loan.

\[
P(Default)=\frac{1}{1+e^{-Z}}
\]

This supports:
- Risk classification
- Loan decision support
- Financial forecasting
- Intelligent loan recommendations

---

# 🛡️ Role-Based Access Control

The system supports multiple administrative roles including:

- President
- Vice President
- Treasurer
- Secretary
- Auditor
- Loan Officer
- Manager
- Viewer

Permissions are controlled dynamically to ensure secure and accountable financial operations.

---

# 📋 Financial Reporting & Analytics

- Savings performance reports
- Loan portfolio analysis
- Contribution compliance analysis
- Risk distribution analytics
- Member reliability tracking
- Financial growth insights

---

# ⚙️ Technology Stack

## Backend
- Django
- Django REST Framework
- PostgreSQL
- Celery
- Redis

## Frontend
- React Native (Expo)
- Tailwind CSS

## DevOps & Infrastructure
- Docker
- Docker Compose
- Nginx
- Certbot
- GitHub Actions CI/CD

## Machine Learning
- Python
- Scikit-learn
- Pandas
- Logistic Regression

---

# 🏗️ System Architecture

```text
Frontend (React Native / Web)
            ↓
REST API (Django REST Framework)
            ↓
Business Logic Layer
            ↓
Savings & Loan Engine
            ↓
AI Credit Risk Prediction Engine
            ↓
PostgreSQL Database
```

---

# 📂 Core Modules

```text
community_system/
│
├── members/
├── savings/
├── loans/
├── meetings/
├── attendance/
├── penalties/
├── reports/
├── notifications/
├── ai_credit_scoring/
├── risk_prediction/
└── analytics/
```

---

# 🔥 Intelligent Loan Workflow

```text
Loan Application
        ↓
Behavioral Data Analysis
        ↓
Credit Score Calculation
        ↓
Probability of Default Prediction
        ↓
Risk Classification
        ↓
Loan Recommendation
        ↓
Approval / Rejection
```

---

# 📈 Risk Classification

| Probability of Default | Risk Level |
|---|---|
| 0.00 – 0.29 | Low Risk |
| 0.30 – 0.59 | Medium Risk |
| 0.60 – 1.00 | High Risk |

---

# 🚀 Setup Instructions

## Clone Repository

```bash
git clone https://github.com/your-username/community-savings-system.git
cd community-savings-system
```

---

## Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create `.env` file:

```env
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:password@localhost:5432/community_db
REDIS_URL=redis://localhost:6379/0
```

---

## Run Migrations

```bash
python manage.py migrate
```

---

## Start Development Server

```bash
python manage.py runserver
```

---

# 📊 Machine Learning Prototype Notice

The Probability of Default prediction module currently uses a synthetic prototype dataset for academic demonstration and testing purposes. The system architecture supports future retraining using real-world cooperative financial datasets for improved predictive accuracy.

---

# 🎓 Academic Contribution

This project demonstrates how machine learning and behavioral financial analytics can be integrated into cooperative financial systems to support intelligent loan decision-making, risk analysis, and financial transparency within community savings environments.

---

# 🔮 Future Improvements

- Real-world dataset integration
- Advanced ML models (Random Forest, XGBoost)
- Explainable AI dashboards
- Mobile money integration
- Real-time notifications
- Fraud detection
- Predictive financial forecasting
- Blockchain-based audit trails

---

# 👨‍💻 Author

AYEMELE ELGOL

Software Engineer | DevOps Engineer | AI & Financial Systems Enthusiast

---

# 📜 License

This project is developed for educational, research, and prototype demonstration purposes.