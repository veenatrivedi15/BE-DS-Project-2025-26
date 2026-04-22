# Carbon Credits Platform - Project Structure Explanation

This document provides a detailed explanation of each component of the Carbon Credits Platform, including directories, files, and their purposes.

## Root Directory

- **CONTEXT.md** - A high-level overview of the project, including its purpose, key components, and technical implementation details.
- **README.md** - Basic information about the project, installation instructions, and getting started guide.
- **login_credentials.txt** - Contains login credentials for various user roles for testing purposes.
- **test_server.py** - A lightweight script for testing the server connection.

## carbon_backend/

The main application directory containing all the Django project files.

- **manage.py** - Django command-line utility for administrative tasks.
- **.env** - Environment variables configuration for the project.
- **requirements.txt** - Lists all Python package dependencies required for the project.
- **db.sqlite3** - SQLite database file containing all project data.
- **build.sh** - Shell script for building and deploying the application.
- **RBAC.md** - Documentation about Role-Based Access Control implemented in the system.
- **folder-structure.txt** - Text file describing the project's folder structure.
- **explanation.md** - Detailed explanations of project components (this file).

### carbon_backend/static/

Contains all static files used in the project.

#### carbon_backend/static/js/

JavaScript files that provide client-side functionality:

- **bank-dashboard.js** (398 lines) - Handles the banking dashboard functionality:
  - Initializes and manages responsive charts for visualizing credit data
  - Manages period selection (weekly, monthly, yearly) with data updates
  - Implements animated counters for statistics
  - Provides touch event handling for mobile devices
  - Manages responsive behavior based on device size

- **bank-reports.js** (761 lines) - Powers the reports generation functionality:
  - Manages the report generation interface
  - Handles filtering and parameter selection
  - Controls data visualization based on selected report types
  - Manages export functionality for CSV and PDF formats
  - Implements responsive UI adjustments for different devices

- **bank-trading.js** (458 lines) - Manages the carbon credit trading functionality:
  - Handles navigation between different trading sections
  - Manages transaction creation, approval, and rejection workflows
  - Updates real-time market data and analytics
  - Implements search and filtering for transactions
  - Provides interactive market analytics visualizations

- **admin-reports.js** (644 lines) - Powers administrator reporting functionality:
  - Manages advanced reporting options for administrators
  - Provides data aggregation and visualization tools
  - Implements export and sharing functionality
  - Controls dashboard elements and interactive filters

- **employee-marketplace.js** (88 lines) - Handles the employee marketplace interface:
  - Manages employee credit browsing and purchasing
  - Handles cart functionality and checkout process
  - Implements filtering and sorting of available credits

- **employer-marketplace.js** (68 lines) - Powers the employer marketplace interface:
  - Manages credit listing and management for employers
  - Handles credit pricing and availability settings
  - Provides transaction history and reporting

- **employee-registration.js** (129 lines) - Manages employee registration process:
  - Handles form validation and submission
  - Implements multi-step registration process
  - Provides real-time validation feedback

- **trip-log.js** (464 lines) - Handles trip logging functionality:
  - Manages trip entry and editing
  - Calculates carbon savings based on transportation methods
  - Provides visualization of trip history and impact
  - Implements geolocation features for trip tracking

- **file-upload.js** (350 lines) - Manages file upload functionality:
  - Handles file selection and validation
  - Implements drag-and-drop interface
  - Provides progress tracking for uploads
  - Manages error handling and success notifications

#### carbon_backend/static/css/

Contains CSS files for styling the application interface.

### carbon_backend/templates/

Contains all HTML templates used in the project.

- **base.html** (646 lines) - The main base template that all other templates extend:
  - Defines the overall page structure and layout
  - Includes common CSS and JavaScript files
  - Implements responsive navigation and header/footer
  - Provides flash message handling

- **landing.html** (318 lines) - The public-facing landing page:
  - Introduces the platform's purpose and benefits
  - Provides sign-up and login access points
  - Showcases platform features and testimonials

#### carbon_backend/templates/bank/

Templates specific to the banking interface:

- **base.html** (65 lines) - Base template for bank-specific pages:
  - Extends the main base template
  - Adds bank-specific navigation and styling
  - Implements bank user authentication

- **dashboard.html** (470 lines) - Banking dashboard interface:
  - Displays key performance metrics and statistics
  - Shows credits issued and transportation mode charts
  - Lists recent transactions with status indicators
  - Provides quick navigation to other banking functions
  - Implements responsive design for all device sizes

- **reports.html** (475 lines) - Reports generation interface:
  - Provides controls for selecting report types and parameters
  - Displays generated report data in visual formats
  - Implements export functionality for reports
  - Features responsive design with mobile optimization

- **trading.html** (1122 lines) - Carbon credit trading interface:
  - Shows marketplace statistics and credit availability
  - Lists pending transactions requiring approval
  - Displays completed transaction history
  - Provides market analytics and visualizations
  - Implements responsive design for all device sizes

- **employers.html** (153 lines) - Employer management interface:
  - Lists registered employers and their status
  - Provides employer detail views and statistics
  - Implements functionality for managing employer accounts

- **profile.html** (153 lines) - Bank profile management:
  - Allows updating of bank account information
  - Provides security settings and preferences
  - Shows account statistics and history

#### carbon_backend/templates/employee/

Templates for employee-facing interfaces.

#### carbon_backend/templates/employer/

Templates for employer-facing interfaces.

#### carbon_backend/templates/admin/

Templates for administrator interfaces.

#### carbon_backend/templates/auth/

Templates for authentication processes including login, registration, and password reset.

#### carbon_backend/templates/components/

Reusable template components used across multiple interfaces:
- Form elements
- Cards and containers
- Navigation components
- Charts and data visualizations
- Modal dialogs and notifications

### carbon_backend/users/

Handles user management, authentication, and authorization:
- User models and database schema
- Authentication views and logic
- Permission management
- User profile functionality

### carbon_backend/trips/

Manages transportation trip logging and carbon calculations:
- Trip models and database schema
- Carbon calculation algorithms
- Trip validation and verification
- Reporting and statistics generation

### carbon_backend/marketplace/

Implements the carbon credit marketplace functionality:
- Credit listing and discovery
- Transaction processing
- Pricing and availability management
- Market analytics and reporting

### carbon_backend/core/

Contains core functionality shared across the application:
- Base models and utilities
- Common middleware and context processors
- System-wide settings and configurations
- Reusable functions and helpers

## Integration Points

The platform has several key integration points between components:

1. **Dashboard to Reports** - The dashboard provides links to detailed reports, passing selected periods and filters.

2. **Trading to Reports** - Trading data is used in generating market analysis reports.

3. **User Authentication to All Components** - Authentication services control access to all parts of the platform based on user roles.

4. **Trip Logging to Marketplace** - Logged trips generate carbon credits that can be traded in the marketplace.

5. **Reporting to Data Export** - Report data can be exported to CSV or PDF formats for external use.

## Mobile Responsiveness

All interfaces implement responsive design principles:

1. **Fluid Layouts** - All pages use percentage-based widths and flex/grid layouts that adapt to screen size.

2. **Breakpoints** - Specific adjustments are made at the following breakpoints:
   - 1200px (large desktops)
   - 992px (small desktops/tablets)
   - 768px (tablets/large phones)
   - 576px (phones)

3. **Touch Optimization** - Mobile interfaces include:
   - Larger touch targets for buttons and controls
   - Swipe gestures for navigation
   - Simplified layouts for smaller screens
   - Touch feedback for interactive elements

4. **Performance Considerations** - Mobile optimization includes:
   - Reduced animation complexity
   - Optimized chart rendering
   - Efficient use of device resources 