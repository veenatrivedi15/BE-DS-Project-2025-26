# 🌍 Carbon Credit Tracking Web Application

## 📘 CONTEXT.md

This document outlines the **project context**, **user roles**, and **feature breakdown** for the Carbon Credit Tracking Web Application.

---

## 👥 User Types and Roles

There are **4 main user roles** in the system:

### 1. Super Admin (System Owner)
- Full control over the platform.
- Manages platform-level settings and database integrity.
- Can create and manage Carbon Bank Admins.
- Monitor system analytics and logs.

### 2. Carbon Bank Admin
- Reviews and approves employer registration requests.
- Monitors carbon credit trading activity.
- Oversees validation for credit trades.
- Can manage marketplace dynamics (pricing policies, caps).

### 3. Employer (Organization Admin)
- Registers organization and office locations.
- Waits for Carbon Bank Admin approval.
- Approves employees who register under them.
- Tracks carbon credits earned by their employees.
- Can buy/sell carbon credits via the marketplace.
- Views reports: employee activity, monthly savings.

### 4. Employee (End User)
- Registers by selecting their employer.
- Waits for employer approval.
- Sets home location and links it to the workplace.
- Logs daily commute trips with transport mode.
- Earns carbon credits based on trip type and distance.
- Views trip history, credits, and graphs.

---

## ✅ Features by User Type

### 🧑‍💼 Super Admin
- System-wide dashboard
- Create Carbon Bank Admins
- Logs & backups

### 🏦 Carbon Bank Admin
- Approve/Reject Employer Registrations
- Manage trading rules, policies
- Monitor employer trading behavior
- View marketplace transactions

### 🏢 Employer Features
- Register company and office location (Google Maps)
- Await bank approval
- Manage employees (approve/deny)
- View employees' carbon point history
- View credits generated per month
- Buy/sell credits with other employers
- Dashboard with organization-wide stats

### 👨‍💼 Employee Features
- Register with home address and employer selection
- Await employer approval
- Log new trip (location, transport mode)
- Upload optional proof (ticket image, etc.)
- See monthly points
- Check past trip logs
- Dashboard: points, savings, graphs

---

## 🚨 Key Functional Considerations

| Problem | Solution |
|--------|----------|
| How to track house ↔ work travel? | Use Geolocation API for GPS logging at start/end |
| How to know the office location? | Set by employer; selectable by employee |
| How to detect transport mode? | User selects manually with proof upload |
| How to calculate distance? | Google Maps API or Haversine Formula |
| Points Calculation? | Based on distance × multiplier (mode-based) |
| How to approve trades? | Admin must verify & approve each credit transfer |

---

## 🧱 Technologies Used

- **Backend:** Django with Django Templates
- **Frontend Enhancement:** HTMX for dynamic interactions
- **Styling:** Tailwind CSS
- **APIs:** Google Maps API, Geolocation API
- **Database:** PostgreSQL or MySQL
- **Authentication:** Django's built-in authentication system
- **Hosting:** Railway / Render

---

## ⚙️ Basic Setup Instructions

### 🔧 Project Setup (Django)
```bash
python -m venv venv
source venv/bin/activate
pip install django django-htmx django-compressor django-tailwind
django-admin startproject carbon_credit_platform
cd carbon_credit_platform
python manage.py startapp core
python manage.py makemigrations && python manage.py migrate

# Set up Tailwind CSS
python manage.py tailwind init
python manage.py tailwind install
python manage.py tailwind start

# Run the server
python manage.py runserver
```

---

## 🧭 Navigation Flow (Simplified)

```
Landing Page
 ├─ Employer Registration
 │   └─ Await Approval (Bank Admin)
 ├─ Employee Registration
 │   └─ Await Approval (Employer)
 ├─ Login → Role-Based Dashboard
     ├─ Carbon Bank Admin → Approve Employers → Monitor Trades
     ├─ Employer → Manage Employees → Track Credits → Trade
     └─ Employee → Log Trip → View History → Track Credits
```

---

## 🎨 Suggested Theme

| Element         | Color Code | Purpose                        |
|----------------|------------|--------------------------------|
| Primary Green  | #2F855A    | Eco-focused identity           |
| Background     | #EDFDF2    | Calm, minty, professional      |
| Accent Teal    | #38B2AC    | Highlight credits & savings    |
| Dark Slate     | #1A202C    | Text and headers               |
| Base White     | #F7FAFC    | Clean sections and contrast    |

---

> This document ensures everyone on the dev team understands roles, responsibilities, and key expectations of the project.